"""ServerStatus.sc"""

import logging

from ..seq import clock as clk
from ..seq import stream as stm
from ..base import model as mdl
from ..base import systemactions as sac
from ..base import responsedefs as rdf
from ..base import functions as fn
from ..base import platform as plt


_logger = logging.getLogger(__name__)


class ServerStatusWatcher():
    def __init__(self, server):
        self.server = server

        self.notified = False
        self._notify = True # @property

        self._alive = False
        self._alive_thread = None
        self._alive_thread_period = 0.7
        self._status_watcher = None

        self.has_booted = False
        self.server_booting = False
        self._unresponsive = False

        self.num_ugens = 0
        self.num_synths = 0
        self.num_groups = 0
        self.num_synthdefs = 0

        self.avg_cpu = None
        self.peak_cpu = None
        self.sample_rate = None
        self.actual_sample_rate = None

        self._really_dead_count = 0
        self._boot_notify_first = True

    def quit(self, on_complete=None, on_failure=False, watch_shutdown=True):
        if watch_shutdown:
            self.watch_quit(on_complete, on_failure)
        else:
            self.stop_status_watcher()
            if on_complete is not None:
                on_complete()
        self.stop_alive_thread()
        self.server_running = False # usa @property
        self.has_booted = False
        self._alive = False
        self.notified = False
        self.server_booting = False
        self._unresponsive = False
        # NOTE: No se si esto sea válido para Python.
        # // server.changed(\serverRunning) should be deferred in dependants!
        # // just in case some don't, defer here to avoid gui updates breaking.
        clk.defer(lambda: mdl.NotificationCenter.notify(self.server, 'server_running'))
        self._boot_notify_first = True

    @property
    def notify(self):
        return self._notify

    @notify.setter
    def notify(self, value):
        self._notify = value
        self.send_notify_request(value)

    # // flag true requests notification, false turns it off
    def send_notify_request(self, flag=True):
        self._send_notify_request(flag, False)

    def do_when_booted(self, on_complete=None, limit=100, on_failure=None):
        # m_bnf = self._boot_notify_first # for not yet implemented
        self._boot_notify_first = False

        def rtn_func():
            while not self.server_running: # BUG: en sclang? server.server_running retorna la propiedad server_running de esta clase...
                # // this is not yet implemented.
                # // or: { serverBooting and: mBootNotifyFirst.not }
                # // and: { (limit = limit - 1) > 0 }
                # // and: { server.applicationRunning.not }
                yield 0.2
            if not self.server_running: # BUG: ídem? NOTE: otra cosa, esto debe ser así por el comentario original de arriba
                post_err = True
                if on_failure is not None:
                    post_err = fn.value(on_failure, self.server) is False
                if post_err:
                    _logger.warning(f"Server '{self.server.name}' on failed to "
                                    "start. You may need to kill all servers")
                self.server_booting = False
                mdl.NotificationCenter.notify(self.server, 'server_running')
            else:
                # // make sure the server process finishes all pending
                # // tasks from Server.tree before running on_complete
                self.server.sync()
                if on_complete is not None:
                    on_complete()

        stm.Routine.run(rtn_func, clk.AppClock)

    def watch_quit(self, on_complete=None, on_failure=None):
        server_really_quit = False

        if self._status_watcher is not None:
            self._status_watcher.disable()
            if self.notified:
                def osc_func(msg, *_):
                    nonlocal server_really_quit
                    if msg[1] == '/quit':
                        if self._status_watcher is not None:
                            self._status_watcher.enable()
                        server_really_quit = True
                        really_quit_watcher.free()
                        if on_complete is not None:
                            on_complete()

                really_quit_watcher = rdf.OSCFunc(
                    osc_func, '/done', self.server.addr)

                def sched_func():
                    if not server_really_quit:
                        if self.unresponsive:
                            _logger.warning(f"Server '{self.server.name}' "
                                            "remained unresponsive during quit")
                        else:
                            _logger.warning(f"Server '{self.server.name}' "
                                            "failed to quit after 3.0 seconds")
                        # // don't accumulate quit-watchers if /done doesn't come back
                        really_quit_watcher.free()
                        if self._status_watcher is not None:
                            self._status_watcher.disable()
                        if on_failure is not None:
                            on_failure(self.server)

                clk.AppClock.sched(3.0, sched_func)

    def add_status_watcher(self):
        if self._status_watcher is None:
            def osc_func(msg, *_):
                if self.notify and not self.notified:
                    self._send_notify_request(True, True)
                self._alive = True
                cmd, one, self.num_ugens, self.num_synths, self.num_groups,\
                    self.num_synthdefs, self.avg_cpu, self.peak_cpu,\
                    self.sample_rate, self.actual_sample_rate = msg

                def defer_func():
                    self.update_running_state(True)
                    mdl.NotificationCenter.notify(self.server, 'counts')

                clk.defer(defer_func)

            resp = rdf.OSCFunc(osc_func, '/status.reply', self.server.addr)
            resp.permanent = True
            self._status_watcher = resp
            self._status_watcher.permanent = True
        else:
            self._status_watcher.enable()

    def stop_status_watcher(self):
        if self._status_watcher is not None:
            self._status_watcher.disable()

    def start_alive_thread(self, delay=0.0):
        self.add_status_watcher()
        if self._alive_thread is None:
            def rtn_func():
                # // this thread polls the server to see if it is alive
                yield delay
                while True:
                    self._alive = False
                    self.server.send_status_msg()
                    yield self._alive_thread_period
                    self.update_running_state(self._alive)
            self._alive_thread = stm.Routine.run(rtn_func, clk.AppClock)
        return self._alive_thread # TODO: por qué hace return de este atributo en sclang?

    def stop_alive_thread(self):
        if self._status_watcher: # is not None, NOTE: pero debería haber algún flag que evite llamar todo esto de nuevo, pj. s.quit() sigue inmprimiendo quit sent
            self._status_watcher.free()
            self._status_watcher = None
        if self._alive_thread is not None:
            self._alive_thread.stop()
            self._alive_thread = None
        self._alive = False

    def resume_thread(self):
        if self._alive_thread is not None:
            self.stop_alive_thread()
            self.start_alive_thread()

    def alive_thread_running(self):
        return self._alive_thread.playing()

    @property
    def server_running(self):
        return self.has_booted and self.notified

    @server_running.setter
    def server_running(self, value):
        if value != self.server_running: # BUG: cambiado server.server_running retorna la propiedad server_running de esta clase...
            self._unresponsive = False
            self.has_booted = value
            if not value:
                #self.has_booted = value # BUG: vuelve a asignar has_booted si running es false, no tiene sentido, es un error.
                sac.ServerQuit.run(self.server)
                self.server.disconnect_shared_memory()
                print('_serverstatus.py: implementar server.recording() L196')
                # if self.server.recording(): # BUG: original es is_recording, así es más pitónico
                #     self.server.stop_recording()
                clk.defer(lambda: mdl.NotificationCenter.notify(self.server, 'did_quit')) # BUG: ver comentario en sclang
                if not self.server.is_local: # BUG: is_local es un atributo en server y un método en NetAddr
                    self.notified = False

    def update_running_state(self, running):
        if self.server.addr.has_bundle():
            clk.defer(lambda: mdl.NotificationCenter.notify(self.server, 'bundling'))
        elif running:
            self.server_running = True
            self.unresponsive = False
            self._really_dead_count = self.server.options.pings_before_considered_dead
        else:
            # // parrot
            self._really_dead_count -= 1
            self.unresponsive = self._really_dead_count <= 0

    @property
    def unresponsive(self):
        return self._unresponsive

    @unresponsive.setter
    def unresponsive(self, value):
        if value != self._unresponsive:
            self._unresponsive = value
            clk.defer(lambda: mdl.NotificationCenter.notify(self.server, 'server_running'))

    # // final actions needed to finish booting
    def _finalize_boot(self):
        # // this needs to be forked so that ServerBoot and ServerTree
        # // will definitely run before notified is true.
        def rtn_func():
            sac.ServerBoot.run(self.server)
            yield from self.server.sync()
            self.server.init_tree()
            self.notified = True
            mdl.NotificationCenter.notify(self.server, 'server_running')
        stm.Routine.run(rtn_func, clk.AppClock)

    # // This method attempts to recover from a loss of client-server contact,
    # // which is a serious emergency in live shows. So it posts a lot of info
    # // on the recovered state, and possibly helpful next user actions.
    def _handle_login_when_already_registered(self, client_id_from_process):
        _logger.info(f'{self.server} - handling login request '
                     'though already registered -')
        if client_id_from_process is None:
            _logger.info(f'{self.server} - notify response did not contain '
                         'already-registered clientID from server process.\n'
                         'Assuming all is well.')
        elif client_id_from_process != self.server.client_id:
            # // By default, only reset clientID if changed,
            # // to leave allocators untouched.
            # // Make sure we can set the clientID, and set it.
            self.notified = False
            self.server.client_id = client_id_from_process
            _logger.info(  # We need to talk about these messages.
                'This seems to be a login after a crash, or from a new server '
                'object, so you may want to release currently running synths '
                'by hand with: server.default_group.release()\n'
                'And you may want to redo server boot finalization by hand:'
                'server.status_watcher._finalize_boot()')
        else:
            # // Same clientID, so leave all server
            # // resources in the state they were in!
            _logger.info(
                'This seems to be a login after a loss of network contact.\n'
                'Reconnected with the same clientID as before, so probably all '
                'is well.')
        # // Ensure that statuswatcher is in the correct state immediately.
        self.notified = True
        self.unresponsive = False
        mdl.NotificationCenter.notify(self.server, 'server_running')

    def _send_notify_request(self, flag=True, adding_status_watcher=False): # BUG: ver este segundo valor por defecto agregado por mi.
        if not self.has_booted:
            return

        # // set up oscfuncs for possible server responses, \done or \failed
        def done(msg, *_):
            new_client_id = msg[2]
            if self.server.options.program == plt.Platform.SCSYNTH_CMD:
                new_max_logins = msg[3]
            else:
                new_max_logins = None
            fail_osc_func.free()
            if new_client_id is not None:
                # // notify on: On registering scsynth sends back a free
                # // clientID and maxLogins this method doesn't fork/wait so
                # // we're still in the clear. Turn notified off (if it was on)
                # // to allow setting clientID.
                self.notified = False
                self.server._handle_client_login_info_from_server(
                    new_client_id, new_max_logins)
                # // XXX: this is a workaround because using `serverBooting`
                # // is not reliable when server is rebooted quickly.
                if adding_status_watcher:
                    self._finalize_boot()
                else:
                    self.notified = True
            else:
                self.notified = False

        done_osc_func = rdf.OSCFunc(
            done, '/done', self.server.addr,
            arg_template=['/notify', None])
        done_osc_func.one_shot()

        def fail(msg, *_):
            done_osc_func.free()
            self.server._handle_notify_fail_string(msg[2], msg)

        fail_osc_func = rdf.OSCFunc(
            fail, '/fail', self.server.addr,
            arg_template=['/notify', None, None])
        fail_osc_func.one_shot()

        self.server.send_msg('/notify', int(flag), self.server.client_id)

        if flag:
            _logger.info("requested notification messages "
                         f"from server '{self.server.name}'")
        else:
            _logger.info("switched off notification messages "
                         f"from server '{self.server.name}'")
