"""ServerStatus.sc"""

import logging
import collections
# import atexit

from ..base import clock as clk
from ..base import stream as stm
from ..base import model as mdl
from ..base import systemactions as sac
from ..base import responsedefs as rdf
from ..base import functions as fn
from ..base import main as _libsc3


_logger = logging.getLogger(__name__)


class ServerStatusWatcher():
    _Action = collections.namedtuple(
        typename='_Action',
        field_names=('on_complete', 'on_failure'))

    def __init__(self, server):
        self.server = server

        self._notified = False

        self._max_logins = None

        self._alive = False
        self._alive_thread = None
        self._alive_thread_period = 0.7
        self.pings_before_dead = 5
        self._really_dead_count = 0
        self._timeout = 3

        self._responder = None

        self._has_booted = False
        self._server_booting = False
        self._server_rebooting = False
        self._server_quitting = False
        self._server_registering = False
        self._server_unregistering = False
        self._unresponsive = False

        self.num_ugens = 0
        self.num_synths = 0
        self.num_groups = 0
        self.num_synthdefs = 0

        self.avg_cpu = None
        self.peak_cpu = None
        self.sample_rate = None
        self.actual_sample_rate = None

        self._clear_actions()

    @property
    def max_logins(self):
        # supernova doesn't return max_logins info.
        return self._max_logins or self.server.options.max_logins

    @property
    def has_booted(self):
        return self._has_booted

    @property
    def server_running(self):
        return self._has_booted and self._notified

    def _set_server_running(self, value):
        if value != self.server_running:
            self._unresponsive = False
            self._has_booted = value
            if not value:
                sac.ServerQuit.run(self.server)
                self.server._disconnect_shm()
                if self.server._recorder.is_recording:
                    self.server._recorder.stop()
                clk.defer(lambda: mdl.NotificationCenter.notify(
                    self.server, 'did_quit')) # BUG: ver comentario en sclang
                if not self.server._is_local:
                    self._notified = False

    @property
    def unresponsive(self):
        return self._unresponsive

    @unresponsive.setter
    def unresponsive(self, value):
        if value != self._unresponsive:
            self._unresponsive = value
            clk.defer(lambda: mdl.NotificationCenter.notify(
                self.server, 'server_running'))

    def _add_action(self, stage, on_complete=None, on_failure=None):
        if stage not in self._boot_actions:
            raise ValueError(f"invalid action stage '{stage}'")
        self._boot_actions[stage].append(self._Action(on_complete, on_failure))

    def _clear_actions(self):
        self._boot_actions = {
            'boot': [], 'quit': [], 'register': [], 'unregister': []}

    def _perform_actions(self, stage, action_name):
        while self._boot_actions[stage]:
            ba = self._boot_actions[stage].pop(0)
            fn.value(getattr(ba, action_name), self.server)

    def _start_alive_thread(self, delay=0.0):
        self._add_responder()
        if self._alive_thread is None:
            def alive_func():
                # // this thread polls the server to see if it is alive
                yield delay
                while True:
                    self._alive = False
                    self.server.send_status_msg()
                    yield self._alive_thread_period
                    self._update_running_state(self._alive)

            self._alive_thread = stm.Routine.run(alive_func, clk.AppClock)

            def start_timeout_func():
                if self._unresponsive:
                    self._stop_alive_thread()
                    _logger.warning(
                        f"'{self.server.name}': registration "
                        "failed, server unresponsive")
                    self._server_booting = False
                    self._server_rebooting = False
                    self._server_registering = False

            clk.AppClock.sched(delay + self._timeout, start_timeout_func)

    def _stop_alive_thread(self):
        if self._responder is not None:
            self._responder.free()
            self._responder = None
        if self._alive_thread is not None:
            self._alive_thread.stop()
            self._alive_thread = None
        self._alive = False
        self._unresponsive = False
        self._really_dead_count = 0
        # atexit.unregister(self.server._unregister_atexit)  # *** BUG: No se puede por _resume_alive_thread.
        self._clear_state_data()

    def _clear_state_data(self):
        self.num_ugens = self.num_synths = self.num_groups =\
        self.num_synthdefs = self.avg_cpu = self.peak_cpu =\
        self.sample_rate = self.actual_sample_rate = None

    def _resume_alive_thread(self):
        if self._alive_thread is not None:
            self._stop_alive_thread()
            self._start_alive_thread()

    @property
    def alive_thread_running(self):
        return self._alive_thread is not None and self._alive_thread.is_playing

    def _add_responder(self):
        if self._responder is None:
            def status_func(msg, *_):
                if not self._notified:
                    self._send_notify_request(True)
                self._alive = True
                cmd, one, self.num_ugens, self.num_synths, self.num_groups,\
                    self.num_synthdefs, self.avg_cpu, self.peak_cpu,\
                    self.sample_rate, self.actual_sample_rate = msg

                def update_state():
                    self._update_running_state(True)
                    mdl.NotificationCenter.notify(self.server, 'counts')

                clk.defer(update_state)

            self._responder = rdf.OscFunc(
                status_func, '/status.reply', self.server.addr)
            self._responder.permanent = True
        else:
            self._responder.enable()

    def _stop_responder(self):
        if self._responder is not None:
            self._responder.disable()

    def _send_notify_request(self, flag=True):
        def done(msg, *_):
            # Is None when /done for flag False.
            new_client_id = msg[2] if len(msg) > 2 else None
            # Supernova doesn't return max logins.
            new_max_logins = msg[3] if len(msg) > 3 else None
            fail_osc_func.free()
            if self._server_booting:
                self._notified = True
                if new_client_id is not None:
                    self._handle_login_done(new_client_id, new_max_logins)
                self._finalize_boot_done()
            elif self._server_registering:
                self._notified = True
                if new_client_id is not None:
                    self._handle_login_done(new_client_id, new_max_logins)
                self._finalize_register_done()
            elif self._server_unregistering:
                self._notified = False
                _logger.info(f"'{self.server.name}': unregistration done")
                self._perform_actions('unregister', 'on_complete')
            else:
                _logger.error(
                    'something went wrong, server status is inconsistent')

        done_osc_func = rdf.OscFunc(
            done, '/done', self.server.addr,
            arg_template=['/notify', None])
        done_osc_func.one_shot()

        def fail(msg, *_):
            fail_string = msg[2]
            # Supernova doesn't return previous id.
            prev_client_id = msg[3] if len(msg) > 3 else None
            done_osc_func.free()
            self._handle_login_fail(fail_string, prev_client_id)
            if self._server_booting:
                self._perform_actions('boot', 'on_failure')
            elif self._server_registering:
                self._perform_actions('register', 'on_failure')
            elif self._server_unregistering:
                self._perform_actions('unregister', 'on_failure')
            else:
                _logger.error(
                    'something went wrong, server status is inconsistent')

        fail_osc_func = rdf.OscFunc(
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
        if not self.server._in_process and new_max_logins is not None:
            self._max_logins = new_max_logins
        _logger.info(
            f"'{self.server.name}': setting client_id to {new_client_id}")
        self.server._set_client_id(new_client_id)

    def _handle_login_fail(self, fail_string, prev_client_id):
        # // post info on some known error cases
        if 'already registered' in fail_string:
            _logger.info(
                f"'{self.server.name}': already registered, "
                f"client_id {prev_client_id}")
            self._unregister()  # Needed to get max_logins from scsynth.
            self._start_alive_thread()
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
        self._stop_alive_thread()
        self._notified = False

    # // final actions needed to finish booting
    def _finalize_boot_done(self):
        # // this needs to be forked so that ServerBoot and ServerTree
        # // will definitely run before _notified is true.
        def finalize_boot_task():
            sac.ServerBoot.run(self.server)
            yield from self.server.sync()
            self.server.init_tree()  # forks
            yield from self.server.sync()
            self._perform_actions('boot', 'on_complete')
            mdl.NotificationCenter.notify(self.server, 'server_running')  # NOTE: esta notificación la hace en varios lugares cuando cambia el estado de running no cuando running es True.

        stm.Routine.run(finalize_boot_task, clk.AppClock)

    def _finalize_register_done(self):
        def finalize_register_task():
            # sac.ServerBoot.run(self.server)  # *** VER SI VA O NO.
            yield from self.server.sync()
            self._perform_actions('register', 'on_complete')

        stm.Routine.run(finalize_register_task, clk.AppClock)

    def _update_running_state(self, running):
        if self.server.addr.has_bundle():
            clk.defer(lambda: mdl.NotificationCenter.notify(
                self.server, 'bundling'))
        elif running:
            self._set_server_running(True)
            self.unresponsive = False
            self._really_dead_count = self.pings_before_dead
        else:
            # // parrot
            self._really_dead_count -= 1
            self.unresponsive = self._really_dead_count <= 0

    def _quit(self, watch_shutdown=True):
        self._stop_alive_thread()
        if watch_shutdown:
            self._watch_quit()
        else:
            self._perform_actions('quit', 'on_complete')
        # Only changes flags affected when quitting.
        self._set_server_running(False)
        self._server_quitting = False
        self._notified = False
        self._max_logins = None
        # // server.changed(\serverRunning) should be deferred in dependants!
        # // just in case some don't, defer here to avoid gui updates breaking.
        clk.defer(lambda: mdl.NotificationCenter.notify(
            self.server, 'server_running'))

    def _watch_quit(self):
        done_quit = False

        if self._notified:
            def quit_func(msg, *_):
                nonlocal done_quit
                if msg[1] == '/quit':
                    done_quit = True
                    quit_watcher.free()
                    _logger.info(f"'{self.server.name}': quit done")
                    self._perform_actions('quit', 'on_complete')

            quit_watcher = rdf.OscFunc(
                quit_func, '/done', self.server.addr)

            def quit_timeout_func():
                if not done_quit:
                    if self.unresponsive:
                        _logger.warning(
                            f"Server '{self.server.name}' "
                            "remained unresponsive during quit")
                    else:
                        _logger.warning(
                            f"Server '{self.server.name}' failed to "
                            f"quit after {self._timeout} seconds")
                    # // don't accumulate quit-watchers
                    # // if /done doesn't come back
                    quit_watcher.free()
                    if self._responder is not None:
                        self._responder.disable()
                    self._perform_actions('quit', 'on_failure')

            clk.AppClock.sched(self._timeout, quit_timeout_func)

    def _unregister(self):
        self._stop_alive_thread()
        self._send_notify_request(False)
        # Same as _quit, only unregistration flags change.
        self._set_server_running(False)
        self._notified = False
        self._max_logins = None
        # // server.changed(\serverRunning) should be deferred in dependants!
        # // just in case some don't, defer here to avoid gui updates breaking.
        clk.defer(lambda: mdl.NotificationCenter.notify(
            self.server, 'server_running'))

    def _boot_nrt(self):
        if not self._has_booted:
            self._has_booted = True
            # sac.ServerBoot.run(self.server)  # Problems.

    def _quit_nrt(self):
        if self._has_booted:
            self._has_booted = False
            # sac.ServerQuit.run(self.server)

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
