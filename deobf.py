import sys
import os.path
from deobf.intruction_mgr import IntructionManger
from deobf.ins_helper import *
from deobf import cfg
from deobf import tracer
from deobf.common_obfuse_detector import CommonOfDetector
from deobf.douyu_obfuse_detcetor import DouyuOfDetector
from deobf.cfg import addr_in_blocks
import shutil


def clear_control_block(fo, obfuses_blocks):
    for ob in obfuses_blocks:
        clean_bytes(fo, ob.start, ob.end)
    #
#


def patch_size_not_enouth(fout, address, max_size, ins_list, ins_mgr, addr2block_can_use):
    block_start_to_use = -1
    n =0
    for start_addr in addr2block_can_use:
        block = addr2block_can_use[start_addr]
        block_sz = block.end - block.start
        fix_jmp = "b #0x%X"%(block.start,)
        n=write_codes(fout, address, max_size, [fix_jmp], ins_mgr)
        if (n > 0 and \
            write_codes(fout, block.start, block_sz, ins_list, ins_mgr) >0):
            block_start_to_use = start_addr
            break
        #
    #
    assert(block_start_to_use > 0)
    print("0x%08X has patch to jump to control block [b 0x%08X]"%(address, block_start_to_use))
    addr2block_can_use.pop(block_start_to_use)
    return n
#

def safe_patch(fout, address, max_size, ins_list, ins_mgr, addr2block_can_use):

    addr_next_insn = write_codes(fout, address, max_size, ins_list, ins_mgr)
    #assert addr_next_insn <= lb.end, "patch %s address :0x%08X to %s error size not enouth"%(code_r, code_last_run.address, fix_code) 
    if(addr_next_insn<=0):

        print("patch address :0x%08X to %r size not enouth try jump to control block"%(address, ins_list))
        addr_next_insn = patch_size_not_enouth(fout, address, max_size, ins_list, ins_mgr, addr2block_can_use)
    #
    else:
        print("patch 0x%08X to [%r] ok"%(address, ins_list))
    #
    return addr_next_insn
#


def safe_patch_last_code_to_lb(fout, nexts_list, lb, codelist, code_last_run, fix_code_list, addr2block_can_use):

    code_r = "%s %s"%(code_last_run.mnemonic, code_last_run.op_str)

    if (is_jmp(code_last_run)):
        clear_itt_if_in_itt(fout, codelist, code_last_run)
        addr_next_insn = safe_patch(fout, code_last_run.address, code_last_run.size, fix_code_list, ins_mgr, addr2block_can_use)
        clean_bytes(fout, addr_next_insn, lb.end)
    #
    else:

        assert(len(lb.childs) == 1) 
        
        child = next(iter(lb.childs))
        child_block_is_lb = False
        for next_addr in nexts_list:
            if (next_addr == child.start):
                child_block_is_lb = True
            #
        #
        
        if (not child_block_is_lb):

            print("last code %s for %r is not jmp patch to next control block %r"%(code_r, lb, child))
            
            addr_next_insn = safe_patch(fout, child.start, child.end, fix_code_list, ins_mgr, addr2block_can_use)
        #
        else:
            #子节点是逻辑块，那就根本不用patch了
            pass
        #
    #
#

def clear_itt_if_in_itt(fout, codelist, code_last_run):
    myindex = codelist.index(code_last_run)
    max_back_find = 4
    l = len(codelist)
    if (l < max_back_find):
        max_back_find = l
    #
    for id in range(myindex, myindex-max_back_find-1, -1):
        c = codelist[id]
        it_count = count_it(c)
        if (it_count>0):
            distance = myindex - id
            
            if (it_count >= distance):
                clean_bytes(fout, c.address, code_last_run.address)
            #
            break
        #
    #
#

def find_addr_in_parent(parents, addr):
    for fake_parent in parents:
        print ("b %r addr 0x%08X"%(fake_parent, addr))
        if (fake_parent.start<=addr and fake_parent.end>addr):
            return fake_parent
        #
    #
    for fake_parent in parents:
        return find_addr_in_parent(fake_parent.parent, addr)
    #
    return None
#

def find_logical_parent(lb, trace):
    start = lb.start
    start_indexes = trace.get_trace_index(start)
    prev_indexes = []
    for index in start_indexes:
        if index > 0:
            prev_indexes.append(index-1)
        #
    #
    logical_parent_b = []
    for prev_index in prev_indexes:
        addr = trace.get_trace_by_index(prev_index)
        print("prev_addr 0x%08X"%addr)

        print("lb %r parent %r"%(lb, lb.parent))
        lpb = find_addr_in_parent(lb.parent, addr)
        logical_parent_b.append(lpb)
    #
    print("find_logical_parent return %r"%logical_parent_b)
    return logical_parent_b
#

def fix_two_jmp_cause_by_two_true_parent(fin, fout, nexts_list, lb, trace, ins_mgr, addr2block_can_use):
    assert len(nexts_list) == 2, "fix_two_jmp_cause_by_two_true_parent"
    parent = find_logical_parent(lb, trace)
    assert len(parent) == 2, "fix_two_jmp_cause_by_two_true_parent %r has %d parent more than two %r"%(lb, len(parent), parent)
    p1b = parent[0]

    p1codelist = get_block_codes(fin, p1b, ins_mgr)
    p1last_code = p1codelist[len(p1codelist) - 1]
    indexs = trace.get_trace_index(p1last_code.address)
    index_need = -1
    for index in indexs:
        address = trace.get_trace_by_index(index+1)
        if (address == lb.start):
            #选取父亲经过自己这个block的路径，开始trace
            index_need = index
            break
        #
    #
    assert(index_need > 0)
    trace_start_index = index_need + 1

    address = trace.get_trace_by_index(trace_start_index)
    while address >= lb.start and address < lb.end:
        address = trace.get_trace_by_index(trace_start_index)
        trace_start_index = trace_start_index + 1
    #
    #该地址为，这个parent块会跑到的地址
    
    print("fix_two_jmp_cause_by_two_true_parent block %r will jump to 0x%08X when pass block %r"%(lb, address, p1b))

    free_reg1 = get_free_regs(p1codelist)
    p2b = parent[1]
    p2codelist = get_block_codes(fin, p2b, ins_mgr)
    free_reg2 = get_free_regs(p2codelist)

    codelist = get_block_codes(fin, lb, ins_mgr)
    free_reg3 = get_free_regs(codelist)

    free_reg = free_reg1 & free_reg2 & free_reg3

    assert len(free_reg)>0, "no free reg can used!!!"

    reg = next(iter(free_reg))
    print("reg %s is choosed"%reg)

    #FIXME 这里的lastcode patch可能覆盖原有有用指令。
    fix_code1 = ["mov %s, #1"%reg, "b #0x%x"%lb.start]
    clear_itt_if_in_itt(fout, p1codelist, p1last_code)
    addr_next_insn = safe_patch(fout, p1last_code.address, p1last_code.size, fix_code1, ins_mgr, addr2block_can_use)
    clean_bytes(fout, addr_next_insn, p1b.end)

    p2last_code = p2codelist[len(p2codelist) - 1]
    fix_code2 = ["mov %s, #0"%reg, "b #0x%x"%lb.start]
    clear_itt_if_in_itt(fout, p2codelist, p2last_code)
    addr_next_insn = safe_patch(fout, p2last_code.address, p2last_code.size, fix_code2, ins_mgr, addr2block_can_use)
    clean_bytes(fout, addr_next_insn, p2b.end)

    nexts_list.remove(address)
    another_branch_traget = nexts_list[0]
    fix_code3 = ["cmp %s, #1"%reg, "beq #0x%x"%address, "b #0x%x"%another_branch_traget]
    last_code = codelist[len(codelist) - 1]
    clear_itt_if_in_itt(fout, codelist, last_code)
    addr_next_insn = safe_patch(fout, last_code.address, last_code.size, fix_code3, ins_mgr, addr2block_can_use)
    clean_bytes(fout, addr_next_insn, lb.end)
#

def patch_common(fin, fout, lb, code_last_run, codelist, trace, ins_mgr, addr2block_can_use):
    n = len(codelist)  
    #TODO:识别所有类型的跳转,现在只支持bxx导致的跳转
    mne = code_last_run.mnemonic
    nexts = trace.get_trace_next(code_last_run.address)#由于trace文件中的指令顺序和index 是完全按照真实执行保存的
    n_next = len(nexts)
    #暂时没见过超过两个的目的地
    assert n_next < 3, "lb %r nexts %r more than 3"%(lb, nexts)
    nexts_list = list(nexts)
    if (n_next == 0):
        print("warning true block %r has no sub true block"%lb)
    elif (n_next == 1):
        #改跳转地址到下一个真实块
        #print(lb.end)
        fix_code = "b #0x%X"%(nexts_list[0],)
        #print(fix_code)
        safe_patch_last_code_to_lb(fout, nexts_list, lb, codelist, code_last_run, [fix_code], addr2block_can_use)
    elif (n_next == 2):
        #TODO:两个目的地，需要根据是否跑过一些指令判断，修正跳转
        print("conditional jmp block")
        #print(lb.start)
        assert not is_jmp_condition(code_last_run), "two destination cause by conditional jump addr [0x%08X] %s %s not support right now"\
        %(code_last_run.address, code_last_run.mnemonic, code_last_run.op_str)
        print ("%r has two destination %r"%(lb, nexts))
        assert(n > 1)
        itt_code = None
        trace_start=-1
        itt_mne = ""
        #从最后找到第一个条件语句
        for id in range(n-1, -1, -1):
            code = codelist[id]
            mne = code.mnemonic
            if (mne.startswith("it")):
                #找到itt之后的语句，然后一步步trace下来
                trace_start = id+1
                itt_code = code
                break
        fix_to_addr1 = -1
        if (trace_start>0):
            code_run_if = codelist[trace_start]
            #从itt下一条指令开始跟踪，根据跟踪到的情况确定跳转过去的条件
            id_if = trace.get_trace_index(code_run_if.address)
            trace_id = id_if[0]
            while True:
                trace_id = trace_id + 1
                addr = trace.get_trace_by_index(trace_id)
                #print (addr,nexts)
                if (addr in nexts):
                    fix_to_addr1 = addr
                    break
            assert(fix_to_addr1 > 0)
            nexts_list.remove(fix_to_addr1)
            fix_to_addr2 = nexts_list[0]
            
            fixed_str1 = "b%s #0x%X"%(itt_code.op_str, fix_to_addr1)
            fixed_str2 = "b #0x%X"%(fix_to_addr2,)
            
            addr_next_insn = safe_patch(fout, itt_code.address, lb.end-itt_code.address, [fixed_str1, fixed_str2], ins_mgr, addr2block_can_use)
            clean_bytes(fout, addr_next_insn, lb.end)
        else:
            print("warning here!!! [%r] has two destination [0x%08X] [0x%08X] cause by two true parent"\
                %(lb, nexts_list[0], nexts_list[1]))
            fix_two_jmp_cause_by_two_true_parent(fin, fout, nexts_list, lb, trace, ins_mgr, addr2block_can_use)
        #
    #
#

def patch_logical_blocks(fin, fout, logic_blocks, obfuses_blocks, trace, ins_mgr):
    addr2ofb = {}
    for ofb in obfuses_blocks:
        addr2ofb[ofb.start] = ofb
    #
    addr2ofb_can_use = {}
    for addr in addr2ofb:
        ofb = addr2ofb[addr]
        is_lb_child = False
        parents = ofb.parent
        for p in parents:
            if (addr_in_blocks(p.start, logic_blocks)):
                is_lb_child = True
                break
            #
        #
        if (not is_lb_child):
            addr2ofb_can_use[addr] = ofb
    #
    
    #print(addr2ofb_can_use)
    clear_control_block(fout, obfuses_blocks)
    #print ("logic_blocks:%r"%logic_blocks)
    for lb in logic_blocks:
        codelist = get_block_codes(fin, lb, ins_mgr)
        n = len(codelist)
        code_last = codelist[n-1]
        mne = code_last.mnemonic
        no_run_blocks = []

        indexes = trace.get_trace_index(lb.start)
        if (len(indexes) < 1):
            print("warning true block %r has not run"%lb)
            no_run_blocks.append(lb)
            continue
        if (is_jmp_imm(code_last)):
            jmp_addr = get_jmp_dest(code_last)
            assert jmp_addr != None, "can not get dest for ins [%s %s] addr:0x%08X"%(code_last.mnemonic, code_last.op_str, code_last.address)
            if (jmp_addr in addr2ofb):#直接调转语句
                patch_common(fin, fout, lb, code_last, codelist, trace, ins_mgr, addr2ofb_can_use)
            #
            elif (is_jmp_condition(code_last) and lb.end in addr2ofb):#条件跳转语句
                patch_common(fin, fout, lb, code_last, codelist, trace, ins_mgr, addr2ofb_can_use)
            #
        #
        elif(lb.end in addr2ofb):
            print ("logic block normal %r"%(lb, ))
            
            code_last_run = None
            ids = []
            for index in range(n-1, -1, -1):
                code_last_run = codelist[index]#由index定位到指令
                ids = trace.get_trace_index(code_last_run.address)
                #找到该块最后一个有执行的指令，patch。
                if len(ids)<=0:
                    print("warning find block end in obfuse block code in block 0x%08X not find in trace"%code_last_run.address)
                else:
                    break
            #
            #patch最后一条执行的指令
            assert(len(ids)>0)
            patch_common(fin, fout, lb, code_last_run, codelist, trace, ins_mgr, addr2ofb_can_use)
        #
    #
#

def list_remove(srclist, listrmove):
    for item in listrmove:
        if (item in srclist):
            srclist.remove(item)
        #
    #
#


if __name__ == "__main__":
    _of_maps = {"common":CommonOfDetector(),"douyu":DouyuOfDetector()}
    if (len(sys.argv)<8):
        print("usage %s <elf_path> <elf_out_path> <trace_path> <func_start_hex> <end_start_hex> <is_thumb> <type> <detector>"%(sys.argv[0]))
        sys.exit(-1)
    #
    path = sys.argv[1]
    out_path = sys.argv[2]
    trace_path = sys.argv[3]
    base_addr = int(sys.argv[4], 16)
    end_addr = int(sys.argv[5], 16)
    is_thumb = sys.argv[6] != "0"
    of_type = sys.argv[7]
    if (len(sys.argv)>7):
        of_type = sys.argv[7]
    #
    detector = _of_maps[of_type]

    lib_name = os.path.basename(path)

    shutil.copyfile(path, out_path)
    with open(path, "rb") as f:
        blocks = cfg.create_cfg(f, base_addr, end_addr - base_addr, is_thumb)
        #print (blocks)
        ins_mgr = IntructionManger(is_thumb)

        of_b, dead_cb = detector.find_ofuse_control_block(f, blocks, base_addr, ins_mgr)

        #print("cbs:%r"%of_b)
        #print ("dead_cb:%r"%dead_cb)
	

        logic_blocks = list(blocks)

        list_remove(logic_blocks, of_b)
        list_remove(logic_blocks, dead_cb)
		
		
        
        print("lbs:%r"%logic_blocks)
        #print (blocks)

        #print ("logic_block:%r"%logic_blocks)

        t = tracer.Tracer(trace_path, lib_name, base_addr, end_addr, logic_blocks)
        with open(out_path, "rb+") as fo:
            codelist = patch_logical_blocks(f, fo, logic_blocks, of_b , t, ins_mgr)
        #
    #
#