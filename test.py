import logging
import sys
from capstone import *
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from androidemu.java.java_class_def import JavaClassDef
from androidemu.emulator import Emulator
from androidemu.java.helpers.native_method import native_method
from androidemu.java.java_class_def import JavaClassDef
from androidemu.java.java_method_def import java_method_def
from androidemu.utils.chain_log import ChainLogger
from androidemu.java.classes.string import String
from androidemu.java.classes.list import List
from androidemu.java.classes.array import Array
# 配置日志相关设置
logging.basicConfig(
    stream=sys.stdout, #标准输出流
    level=logging.DEBUG, #输出等级
    format="%(asctime)s %(levelname)7s %(name)34s | %(message)s" #输出格式
)
 
class JniMakeUrl(metaclass=JavaClassDef, jvm_name='com/douyu/lib/http'):
    def __init__(self):
        pass
 
     #print('# Tracing instruction at 0x%x, instruction size = 0x%x, instruction = %s' % (address, size, instruction_str))
    # if(address-module.base==0x3454 and flag_1==1):
        # #remote_ins=mu.mem_read(0x01000023,10)
        # tmp_address=mu.reg_read(UC_ARM_REG_PC)
        # mu.reg_write(UC_ARM_REG_R3,0x01000023)
        # flag_1+=1
        # #for ins in cp.disasm(remote_ins,0x01000023):
            # #print("remote  0x%08x:\t%s\t%s"%(ins.address,ins.mnemonic,ins.op_str))
    # if(address-module.base==0x34e2 and flag_2==1):
        # mu.reg_write(UC_ARM_REG_R5,0x7AABC3EE)
        # mu.reg_write(UC_ARM_REG_R0,0x5B847126)
        # flag_2+=1
logger = logging.getLogger(__name__) #实例化对象
 
# 实例化虚拟机
emulator = Emulator()
 
#加载Libc库
#emulator.load_library("example_binaries/libc.so", do_init=False)
 
#加载要模拟器的库
lib_module = emulator.load_library("样本2.so")
 
#打印已经加载的模块
logger.info("Loaded modules:")
for module in emulator.modules:
    logger.info("[0x%x] %s" % (module.base, module.filename))
 
 
#trace 每步执行的指令, 方便调试, 其实也可以取消
def hook_code(mu, address, size, user_data):
    cp=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    flag_1=1
    flag_2=1
    instruction = mu.mem_read(address, size)
    instruction_str = ''.join('{:02x} '.format(x) for x in instruction)
    for ins in cp.disasm(instruction,address):
        print("]0x%08x:\t%s\t%s"%(ins.address-module.base,ins.mnemonic,ins.op_str))
emulator.mu.hook_add(UC_HOOK_CODE, hook_code)
 
emulator.java_classloader.add_class(JniMakeUrl)
#通过导出符号来调用函数
emulator.call_symbol(lib_module, 'add')
 
#通过R0来获取调用结构
#print("String length is: %i" % emulator.mu.reg_read(UC_ARM_REG_R0))