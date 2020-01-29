"""ServerStatus.sc"""

import logging
import collections

from ..seq import clock as clk
from ..seq import stream as stm
from ..base import model as mdl
from ..base import systemactions as sac
from ..base import responsedefs as rdf
from ..base import functions as fn
from ..base import main as _libsc3


_logger = logging.getLogger(__name__)


class ServerStatusWatcher():
    _BootAction = collections.namedtuple(
        typename='BootAction',
        field_names=('on_complete', 'on_failure'))

    def __init__(self, server):
        self.server = server

        self.notified = False

        self._max_logins = None

        self._alive = False
        self._alive_thread = None
        self._alive_thread_period = 0.7
        self._responder = None

        self.has_booted = False
        self.server_booting = False
        self.server_quiting = False
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
        self._boot_actions = []

    @property
    def max_logins(self):
        # supernova doesn't return max_logins info.
        return self._max_logins or self.server.options.max_logins

    @property
    def server_running(self):
        return self.has_booted and self.notified

    @server_running.setter
    def server_running(self, value):
        if value != self.server_running:
            self._unresponsive = False
            self.has_booted = value
            if not value:
                sac.ServerQuit.run(self.server)
                self.server._disconnect_shared_memory()
                if self.server._recorder.is_recording():
                    self.server._recorder.stop_recording()
                clk.defer(lambda: mdl.NotificationCenter.notify(
                    self.server, 'did_quit')) # BUG: ver comentario en sclang
                if not self.server.is_local: # BUG: is_local es un atributo en server y un método en NetAddr
                    self.notified = False

    @property
    def unresponsive(self):
        return self._unresponsive

    @unresponsive.setter
    def unresponsive(self, value):
        if value != self._unresponsive:
            self._unresponsive = value
            clk.defer(lambda: mdl.NotificationCenter.notify(
                self.server, 'server_running'))

    def _add_boot_action(self, on_complete=None, on_failure=None):
        self._boot_actions.append(self._BootAction(on_complete, on_failure))

    def _clear_boot_actions(self):
        self._boot_actions = []

    def _perform_boot_actions(self, action_name=None):
        while self._boot_actions:
            ba = self._boot_actions.pop(0)
            fn.value(getattr(ba, action_name), self.server)

    def start_alive_thread(self, delay=0.0):
        self.add_responder()
        if self._alive_thread is None:
            def alive_func():
                # // this thread polls the server to see if it is alive
                yield delay
                while True:
                    self._alive = False
                    self.server.send_status_msg()
                    yield self._alive_thread_period
            self._alive_thread = stm.Routine.run(alive_func, clk.AppClock)

    def stop_alive_thread(self):
        if self._responder is not None:
            self._responder.free()
            self._responder = None
        if self._alive_thread is not None:
            self._alive_thread.stop()
            self._alive_thread = None
        self._alive = False

    def resume_alive_thread(self):
        if self._alive_thread is not None:
            self.stop_alive_thread()
            self.start_alive_thread()

    def alive_thread_running(self):
        return self._alive_thread is not None and self._alive_thread.playing()

    def add_responder(self):
        if self._responder is None:
            def status_func(msg, *_):
                if not self.notified:
                    self._send_notify_request(True)
                self._alive = True
                cmd, one, self.num_ugens, self.num_synths, self.num_groups,\
                    self.num_synthdefs, self.avg_cpu, self.peak_cpu,\
                    self.sample_rate, self.actual_sample_rate = msg

                def update_state():
                    self._update_running_state(True)
                    mdl.NotificationCenter.notify(self.server, 'counts')

                clk.defer(update_state)

            self._responder = rdf.OSCFunc(
                status_func, '/status.reply', self.server.addr)
            self._responder.permanent = True
        else:
            self._responder.enable()

    def stop_responder(self):
        if self._responder is not None:
            self._responder.disable()

    def _send_notify_request(self, flag=True):
        def done(msg, *_):
            # Is None when /done for flag False.
            new_client_id = msg[2] if len(msg) > 2 else None
            # Supernova don't returns max logins.
            new_max_logins = msg[3] if len(msg) > 3 else None
            fail_osc_func.free()
            if new_client_id is not None:
                self._handle_login_done(new_client_id, new_max_logins)
                if self.server_booting:
                    self._finalize_boot_done()
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
            self._handle_login_fail(msg)
            self._finalize_boot_fail()

        fail_osc_func = rdf.OSCFunc(
            fail, '/fail', self.server.addr,
            arg_template=['/notify', None, None])
        fail_osc_func.one_shot()

        self.server.send_msg('/notify', int(flag), self.server.client_id)

        if flag:
            _logger.info(f"'{self.server.name}': requested registration id")
        else:
            _logger.info(f"'{self.server.name}': requested id unregistration")

    def _handle_login_done(self, new_client_id, new_max_logins):
        # // only set maxLogins if not internal server
        if not self.server.in_process and new_max_logins is not None:
            self._max_logins = new_max_logins
        _logger.info(
            f"'{self.server.name}': setting client_id to {new_client_id}")
        self.server._set_client_id(new_client_id)

    def _handle_login_fail(self, msg):
        fail_string = msg[2]
        # // post info on some known error cases
        if 'already registered' in fail_string:
            _logger.info(
                f"'{self.server.name}': already registered, client_id {msg[3]}")
            self._unregister()  # Needed to get max_logins from scsynth.
            self.start_alive_thread()
            return
        elif 'not registered' in fail_string:
            # // unregister when already not registered:
            _logger.info(f"'{self.server.name}': not registered")
        elif 'too many users' in fail_string:
            _logger.info(
                f"'{self.server.name}': failed to register, too many users")
        else:
            # // throw error if unknown failure
            # raise Exception(  # gives an uncaught exception in a fork.
            _logger.warning(f"'{self.server.name}': failed to register")
        self.stop_alive_thread()
        self.notified = False

    # // final actions needed to finish booting
    def _finalize_boot_done(self):
        # // this needs to be forked so that ServerBoot and ServerTree
        # // will definitely run before notified is true.
        def finalize_task():
            sac.ServerBoot.run(self.server)
            yield from self.server.sync()
            self.server.init_tree()  # forks
            yield from self.server.sync()
            self.notified = True
            self._perform_boot_actions('on_complete')
            mdl.NotificationCenter.notify(self.server, 'server_running')  # NOTE: esta notificación la hace en varios lugares cuando cambia el estado de running no cuando running es True.

        stm.Routine.run(finalize_task, clk.AppClock)

    def _finalize_boot_fail(self):
        self._perform_boot_actions('on_failure')

    def _update_running_state(self, running):
        if self.server.addr.has_bundle():
            clk.defer(lambda: mdl.NotificationCenter.notify(
                self.server, 'bundling'))
        elif running:
            self.server_running = True
            self.unresponsive = False
            self._really_dead_count = self.server.options.pings_before_considered_dead
        else:
            # // parrot
            self._really_dead_count -= 1
            self.unresponsive = self._really_dead_count <= 0

    def _quit(self, on_complete=None, on_failure=False, watch_shutdown=True):
        if watch_shutdown:
            self._watch_quit(on_complete, on_failure)
        else:
            self.stop_responder()
            fn.value(on_complete, self.server)
        self.stop_alive_thread()
        self.server_running = False # usa @property
        # self.has_booted = False
        self.server_booting = False
        self.server_quiting = False
        # self._alive = False
        self.notified = False
        self._unresponsive = False
        self._max_logins = None
        # // server.changed(\serverRunning) should be deferred in dependants!
        # // just in case some don't, defer here to avoid gui updates breaking.
        clk.defer(lambda: mdl.NotificationCenter.notify(
            self.server, 'server_running'))

    def _watch_quit(self, on_complete=None, on_failure=None):
        server_really_quit = False

        if self._responder is not None:
            self._responder.disable()
            if self.notified:
                def quit_func(msg, *_):
                    nonlocal server_really_quit
                    if msg[1] == '/quit':
                        if self._responder is not None:
                            self._responder.enable()
                        server_really_quit = True
                        quit_watcher.free()
                        fn.value(on_complete, self.server)

                quit_watcher = rdf.OSCFunc(
                    quit_func, '/done', self.server.addr)

                def quit_timeout_func():
                    if not server_really_quit:
                        if self.unresponsive:
                            _logger.warning(f"Server '{self.server.name}' "
                                            "remained unresponsive during quit")
                        else:
                            _logger.warning(f"Server '{self.server.name}' "
                                            "failed to quit after 3.0 seconds")
                        # // don't accumulate quit-watchers
                        # // if /done doesn't come back
                        quit_watcher.free()
                        if self._responder is not None:
                            self._responder.disable()
                        fn.value(on_failure, self.server)

                clk.AppClock.sched(3.0, quit_timeout_func)

    def _unregister(self):
        self.stop_alive_thread()
        self._send_notify_request(False)
        # Same as _quit
        self.server_running = False # usa @property
        # self.has_booted = False
        # self.server_booting = False
        # self.server_quiting = False
        # self._alive = False
        # self.notified = False
        self._unresponsive = False
        self._max_logins = None
        # // server.changed(\serverRunning) should be deferred in dependants!
        # // just in case some don't, defer here to avoid gui updates breaking.
        clk.defer(lambda: mdl.NotificationCenter.notify(
            self.server, 'server_running'))


    ### Utilities ###

    def ping(self, n=1, wait=0.1, action=None):
        if not self.server_running:
            _logger.info(f"server '{self.server.name}' not running")
            return

        result = 0

        def task():
            nonlocal n, result
            t = _libsc3.main.elapsed_time()
            yield from self.server.sync()
            dt = _libsc3.main.elapsed_time() - t
            _logger.info(f'measured latency: {dt}s')
            result = max(result, dt)
            n -= 1
            if n > 0:
                clk.SystemClock.sched(wait, lambda: ping_func())
            else:
                _logger.info(
                    f"maximum determined latency of server "
                    f"'{self.server.name}': {result} seconds")
                fn.value(action, result)

        def ping_func():
            stm.Routine.run(task, clk.SystemClock)

        ping_func()
