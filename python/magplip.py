# magplip - run magplip protocol on parallel port

import vpar
import time
import datetime

MAGIC=0x42
CRC=0x01
NO_CRC=0x02

class MagPlipError(Exception):
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

class MagPlip:
    def __init__(self, v):
        self.vpar = v
    
    def start(self):
        # clear HS_LINE
        self.vpar.clr_control_mask(vpar.BUSY_MASK)
    
    def wait_select(self, value, timeout=1):
        """wait for SELECT signal"""
        t = time.time()
        end = t + timeout
        found = False
        while t < end:
            s = self.vpar.peek_control() & vpar.SEL_MASK
            if s and value:
                found = True
                break
            elif not s and not value:
                found = True
                break
                
            rem = end - t
            self.vpar.poll_state(rem)
            t = time.time()
        return found
    
    def wait_line_toggle(self, expect, timeout=1):
        """wait for toggle on POUT signal"""
        #print expect
        t = time.time()
        end = t + timeout
        found = False
        while t < end:
            s = self.vpar.peek_control()
            if expect and ((s & vpar.POUT_MASK) == vpar.POUT_MASK):
                found = True
                break
            elif (not expect) and ((s & vpar.POUT_MASK) == 0):
                found = True
                break
            
            # check for SELECT -> arbitration loss?
            if (s & vpar.SEL_MASK) != vpar.SEL_MASK:
                return False
                
            rem = end - t
            self.vpar.poll_state(rem)
            t = time.time()
        return found
    
    def toggle_busy(self, value):
        if value:
            self.vpar.clr_control_mask(vpar.BUSY_MASK)
        else:
            self.vpar.set_control_mask(vpar.BUSY_MASK)
            
    def set_next_byte(self, toggle_expect, value, timeout=1):
        ok = self.wait_line_toggle(toggle_expect, timeout)
        if not ok:
            return False
        self.vpar.set_data(value)
        self.toggle_busy(toggle_expect)
        return True

    def set_next_word(self, toggle_expect, value, timeout=1):
        v1 = value / 256
        ok = self.set_next_byte(toggle_expect, v1, timeout)
        if not ok:
            return False
        v2 = value % 256
        ok = self.set_next_byte(not toggle_expect, v2, timeout)
        return ok

    def get_next_byte(self, toggle_expect, timeout=1):
        ok = self.wait_line_toggle(toggle_expect, timeout)
        if not ok:
            return None
        self.vpar.poll_state(0)
        data = self.vpar.peek_data()
        self.toggle_busy(not toggle_expect)
        return data
    
    def get_next_word(self, toggle_expect, timeout=1):
        v1 = self.get_next_byte(toggle_expect, timeout)
        if v1 == None:
            return None
        v2 = self.get_next_byte(not toggle_expect, timeout)
        if v2 == None:
            return None
        return v1 * 256 + v2

    # ----- public API ----

    def send(self, raw_pkt, timeout=1, crc=False):
        """send a packet via vpar port"""
        # set HS_LINE (BUSY)
        self.vpar.set_control_mask(vpar.BUSY_MASK)
        # set magic byte
        self.vpar.set_data(MAGIC)
        # pulse ACK -> trigger IRQ in server
        trigger = time.time()
        self.vpar.trigger_ack()
        try:
            # wait for select
            ok = self.wait_select(True, timeout)
            if not ok:
                raise MagPlipError("tx ERROR: Waiting for select")
            start = time.time()
            first_delta = start - trigger
            # set byte for magic code NO_CRC
            ok = self.set_next_byte(True, 0x02, timeout)
            if not ok:
                raise MagPlipError("tx ERROR: CRC flag")
            # send size
            size = len(raw_pkt) + 2 # add crc
            ok = self.set_next_word(False, size, timeout)
            if not ok:
                raise MagPlipError("tx ERROR: size value")
            # send CRC
            crc = 0
            ok = self.set_next_word(False, crc, timeout)
            if not ok:
                raise MagPlipError("tx ERROR: CRC value")
            # send data
            toggle = False
            pos = 0
            for a in raw_pkt:
                ok = self.set_next_byte(toggle, ord(a), timeout)
                if not ok:
                    raise MagPlipError("tx ERROR: data @%d" % pos)
                toggle = not toggle
                pos += 1
            # wait for final toggle
            ok = self.wait_line_toggle(toggle, timeout)
            if not ok:
                raise MagPlipError("tx ERROR: final toggle")
            end = time.time()
            data_delta = end - start
            # wait for select end
            ok = self.wait_select(False, timeout)
            if not ok:
                raise MagPlipError("tx ERROR: Waiting for unselect")
            last = time.time()
            last_delta = last - end
            return (first_delta, data_delta, last_delta)
        finally:
            # clear HS_LINE (BUSY)
            self.vpar.clr_control_mask(vpar.BUSY_MASK, timeout=1)

    def recv(self, timeout=1):
        """receive a data packet via vpar port. make sure to call can_recv() before!!"""
        try:
            first = time.time()
            # first assume SELECT to be set
            ok = self.wait_select(True, timeout)
            if not ok:
              return None,None
            start = time.time()
            first_delta = start - first
            # get magic byte
            magic = self.get_next_byte(True, timeout)
            if not magic:
                raise MagPlipError("rx ERROR: no magic")
            # get crc mode
            crc_mode = self.get_next_byte(False, timeout)
            if not crc_mode:
                raise MagPlipError("rx ERROR: no crc mode")
            if crc_mode < 1 or crc_mode > 2:
                raise MagPlipError("rx ERROR: invalid CRC mode: %d" % crc_mode)
            # get size
            size = self.get_next_word(True, timeout)
            if size == None:
                raise MagPlipError("rx ERROR: no size")
            # get crc
            crc = self.get_next_word(True, timeout)
            if crc == None:
                raise MagPlipError("rx ERROR: no crc value")
            size -= 2 # skip crc
            # get data
            toggle = True
            pos = 0
            raw_pkt = ""
            for i in xrange(size):
                d = self.get_next_byte(toggle, timeout)
                if d == None:
                    raise MagPlipError("rx ERROR: data @%d" % pos)
                raw_pkt += chr(d)
                toggle = not toggle
                pos = pos+1
            end = time.time()
            data_delta = end - start
            # wait for select gone
            ok = self.wait_select(False, timeout)
            if not ok:
                raise MagPlipError("rx ERROR: no unselect")
            last = time.time()
            last_delta = last - end
            return raw_pkt,(first_delta, data_delta, last_delta)
        finally:
            # clear BUSY
            self.vpar.clr_control_mask(vpar.BUSY_MASK, timeout=1)

