from deobf.intruction_mgr import IntructionManger
from deobf.ins_helper import *
from deobf import cfg
from deobf import tracer

def _start_withs(str, sets):
    for s in sets:
        if (str.startswith(s)):
            return True
        #
    #
    return False
#

class CommonOfDetector:
    def __init__(self):
        pass
    #

    def find_ofuse_control_block(self, f, blocks, base_addr, ins_mgr):
        obfuses_cb = []
        dead_cb = []
         
        for b in blocks:
            #print(b)

            codelist = get_block_codes(f, b, ins_mgr)
            #print(codelist[0].mnemonic)
            n = len(codelist)

            if (n < 2):
            #只有一条指令而且跳回给自己的是死块
                if (n == 1):
                    jmp_addr = get_jmp_dest(codelist[0])
                    if (jmp_addr != None and jmp_addr == b.start):
                        dead_cb.append(b)
                        continue
                    #
                #
            #
            #if (n < 6):
            code_last = codelist[n-1]#获得最后一条指令
            
            maybe_cb = False
            tbl_jmp = ("tbb", "tbb.h", "tbh", "tbh.w")
            #if this block has cmp, itt, etc, maybe is a control block
            suspect_ins = ("cmp", "it", "itt", "ittt", "itttt")
            if (n==1 and code_last.mnemonic[0] == "b" or code_last.mnemonic in ("cbz", "cbnz",'beq') or code_last.mnemonic in tbl_jmp):
                maybe_cb = True
            elif ( code_last.mnemonic in ("cbz", "cbnz",'beq','beq.w')):
                maybe_cb = True
            is_cb = maybe_cb
			# for j in range(n-1):
                    # mne = codelist[j].mnemonic
                    
                    # if (mne in suspect_ins):
                        # maybe_cb = True
                        # break
			#code_last.mnemonic[0] == "b"
            # mem_cmds = set(["str", "ldr", "push", "pop", "bl", "blx"])
            # if (maybe_cb):
                # for j in range(0, n):
                    # mne = codelist[j].mnemonic
                    # if (_start_withs(mne, mem_cmds)):
                        # if (mne.startswith("beq")):
                            # continue
                        # #
                        # if (n>4):
                            # is_cb = False
                            # break
            if (is_cb):
                obfuses_cb.append(b)
            #

        #
		
        return obfuses_cb, dead_cb
    #
#