

class Server(...):
    def __init__(self, ...):
        ...
        self.sync_thread = None # solo getter en la declaración # se usa en sched_sync
        self.sync_tasks = [] # solo getter en la declaración # se usa en sched_sync
        ...

    ...

    ### Network messages ###

    # def send_raw(self, raw_bytes): # send a raw message without timestamp to the addr.
    #    self.addr.send_raw(raw_bytes)

    def send_msg_sync(self, condition, *args):  # utility
        # Or the name was misleading and implementation was sending bundles,
        # which is more practical but misnamed. Sending bundles sync was for
        # the first msg only. To restore it is trivial.
        # This method just sends one msg following send_msg method above.
        # BUG: If the msg or this method fails (e.g. becuase msg is invalid)
        # BUG: resp_func will be active forever.
        condition = condition or stm.Condition()
        cmd_name = args[0]
        args = list(args)

        def resp_func(msg, *_):
            if str(msg[1]) == cmd_name:
                resp.free()
                condition.test = True
                condition.signal()

        resp = rdf.OSCFunc(resp_func, '/done', self.addr)
        self.send_msg(*args)
        yield from condition.wait()

    def sched_sync(self, func):  # utility
        # Not used in library. It creates two attributes to server.
        self.sync_tasks.append(func)
        if self.sync_thread is None:
            def sync_thread_rtn():
                cond = stm.Condition()
                while len(self.sync_tasks) > 0:
                    yield from self.sync_tasks.pop(0)(cond)
                self.sync_thread = None
            self.sync_thread = stm.Routine.run(sync_thread_rtn, clk.AppClock)

    # def list_send_msg(self, msg): # redudant, confusing
    #     ...
    # def list_send_bundle(self, time, msgs): # redudant, confusing
    #     ...

    ### Scheduling ###

    def wait(self, response_name):
        cond = stm.Condition()

        def resp_func(*_):
            cond.test = True
            cond.signal()

        rdf.OSCFunc(resp_func, response_name, self.addr).one_shot()
        yield from cond.wait()

    # wait_for_boot, is the same as boot except no on_complete if running
    # do_when_booted, is _status_watcher._add_boot_action
    # if_running, No.
    # if_not_running, No.

    def boot_sync(self, condition=None):
        condition = condition or stm.Condition()
        condition.test = False

        def func():
            condition.test = True
            condition.signal()

        self.wait_for_boot(func)
        yield from condition.wait()

    def cached_buffers_do(self, func):
        bff.Buffer.cached_buffers_do(self, func)

    def cached_buffer_at(self, bufnum):
        return bff.Buffer.cached_buffer_at(self, bufnum)
