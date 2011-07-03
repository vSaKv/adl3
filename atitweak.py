import sys
from optparse import OptionParser
from adl3 import *

class ADLError(Exception):
    pass

adapters = []

def initialize():
    # the '1' means only retrieve info for active adapters
    if ADL_Main_Control_Create(ADL_Main_Memory_Alloc, 1) != ADL_OK:
        raise ADLError("Couldn't initialize ADL interface.")

def shutdown():
    if ADL_Main_Control_Destroy() != ADL_OK:
        raise ADLError("Couldn't destroy ADL interface global pointers.")

def get_adapter_info():
    adapter_info = []
    
    num_adapters = c_int(-1)
    if ADL_Adapter_NumberOfAdapters_Get(byref(num_adapters)) != ADL_OK:
        raise ADLError("ADL_Adapter_NumberOfAdapters_Get failed.")

    # allocate an array of AdapterInfo, see ctypes docs for more info
    info = (AdapterInfo * num_adapters.value)() 
    
    # AdapterInfo_Get grabs info for ALL adapters in the system
    if ADL_Adapter_AdapterInfo_Get(cast(info, LPAdapterInfo), sizeof(info)) != ADL_OK:
        raise ADLError("ADL_Adapter_AdapterInfo_Get failed.")

    for adapter_index in range(0, num_adapters.value):
        status = c_int(-1)
        if ADL_Adapter_Active_Get(adapter_index, byref(status)) != ADL_OK:
            raise ADLError("ADL_Adapter_Active_Get failed.")

        # save it in our list if it's active
        if status.value == ADL_TRUE:
            adapter_info.append(info[adapter_index])
    
    return adapter_info

def list_adapters(adapter_list=None):
    adapter_info = get_adapter_info()
    
    for index, info in enumerate(adapter_info):
        if adapter_list is None or index in adapter_list:
            print "%d. %s (%s)" % (index, info.strAdapterName, info.strDisplayName)
            
            od_parameters = ADLODParameters()
            od_parameters.iSize = sizeof(od_parameters)
            
            if ADL_Overdrive5_ODParameters_Get(info.iAdapterIndex, byref(od_parameters)) != ADL_OK:
                raise ADLError("ADL_Overdrive5_ODParameters_Get failed.")
                
            print "    engine clock range is %g - %gMHz" % (od_parameters.sEngineClock.iMin/100.0,od_parameters.sEngineClock.iMax/100.0)
            print "    memory clock range is %g - %gMHz" % (od_parameters.sMemoryClock.iMin/100.0, od_parameters.sMemoryClock.iMax/100.0)
            print "    core voltage range is %g - %gVDC" % (od_parameters.sVddc.iMin/1000.0, od_parameters.sVddc.iMax/1000.0)
    
#            fan_speed_info = ADLFanSpeedInfo()
#            fan_speed_info.iSize = sizeof(fan_speed_info)
#    
#            if ADL_Overdrive5_FanSpeedInfo_Get(info.iAdapterIndex, 0, fan_speed_info) != ADL_OK:
#                raise ADLError("ADL_Overdrive5_FanSpeedInfo_Get failed.")
    
            if od_parameters.iDiscretePerformanceLevels:
                plevels = ADLODPerformanceLevels()
                plevels_size = sizeof(ADLODPerformanceLevels) + sizeof(ADLODPerformanceLevel) * (od_parameters.iNumberOfPerformanceLevels -1)
                resize(plevels, plevels_size)
                plevels.iSize = plevels_size
        
                if ADL_Overdrive5_ODPerformanceLevels_Get(info.iAdapterIndex, 0, byref(plevels)) != ADL_OK:
                    raise ADLError("ADL_Overdrive5_ODPerformanceLevels_Get failed.")
        
                levels = cast(plevels.aLevels, POINTER(ADLODPerformanceLevel))
        
                for index in range(0, od_parameters.iNumberOfPerformanceLevels):
                    print "    performance level %d: engine clock %gMHz, memory clock %gMHz, core voltage %gVDC" % (index,
                                                                                                                levels[index].iEngineClock/100.0,
                                                                                                                levels[index].iMemoryClock/100.0,
                                                                                                                levels[index].iVddc/1000.0)

def set_plevels(adapter_list=None,
                plevel_list=None,
                engine_clock=None,
                memory_clock=None,
                core_voltage=None):
    adapter_info = get_adapter_info()

    for adapter_index, info in enumerate(adapter_info):
        if adapter_list is None or adapter_index in adapter_list:
            od_parameters = ADLODParameters()
            od_parameters.iSize = sizeof(od_parameters)
            
            if ADL_Overdrive5_ODParameters_Get(info.iAdapterIndex, byref(od_parameters)) != ADL_OK:
                raise ADLError("ADL_Overdrive5_ODParameters_Get failed.")
                
            if od_parameters.iDiscretePerformanceLevels:
                plevels = ADLODPerformanceLevels()
                plevels_size = sizeof(ADLODPerformanceLevels) + sizeof(ADLODPerformanceLevel) * (od_parameters.iNumberOfPerformanceLevels -1)
                resize(plevels, plevels_size)
                plevels.iSize = plevels_size
        
                if ADL_Overdrive5_ODPerformanceLevels_Get(info.iAdapterIndex, 0, byref(plevels)) != ADL_OK:
                    raise ADLError("ADL_Overdrive5_ODPerformanceLevels_Get failed.")
        
                levels = cast(plevels.aLevels, POINTER(ADLODPerformanceLevel))
                
                for plevel_index in range(0, od_parameters.iNumberOfPerformanceLevels):
                    if plevel_list is None or plevel_index in plevel_list:
                        message = []
                        
                        if engine_clock is not None:
                            levels[plevel_index].iEngineClock = int(engine_clock*100.0)
                            message.append("engine clock %gMHz" % engine_clock)
                        if memory_clock is not None:
                            levels[plevel_index].iMemoryClock = int(memory_clock*100.0)
                            message.append("memory clock %gMHz" % memory_clock)
                        if core_voltage is not None:
                            levels[plevel_index].iVddc = int(core_voltage*1000.0)
                            message.append("core voltage %gVDC" % core_voltage)
                        
                        print "Setting performance level %d on adapter %d: %s" % (plevel_index,
                                                                                  adapter_index,
                                                                                  ", ".join(message))
                        
                # set the performance levels for this adapter            
                if ADL_Overdrive5_ODPerformanceLevels_Set(info.iAdapterIndex, byref(plevels)) != ADL_OK:
                    raise ADLError("ADL_Overdrive5_ODPerformanceLevels_Set failed.")
                
            else:
                print "Adapter %d does not support discrete performance levels." % adapter_index
    

if __name__ == "__main__":
    usage = "usage: %prog [options]"
    
    parser = OptionParser(usage=usage)
    
    parser.add_option("-l", "--list-adapters", dest="action", action="store_const", const="list_adapters",
                      help="Lists all detected and supported display adapters.")

    parser.add_option("-e", "--set-engine-clock", dest="engine_clock", type="float", action="store", default=None,
                      help="Sets engine clock speed (in MHz) for the selected performance levels on the " 
                           "selected adapters.")
    parser.add_option("-m", "--set-memory-clock", dest="memory_clock", type="float", action="store", default=None,
                      help="Sets memory clock speed (in MHz) for the selected peformance levels on the " 
                           "selected adapters.")
    parser.add_option("-v", "--set-core-voltage", dest="core_voltage", type="float", action="store", default=None,
                      help="Sets core voltage level (in VDC) for the selected performance levels on the "
                           "selected adapters.""")
    
    parser.add_option("-A", "--adapter", dest="adapter_list", default="all", metavar="ADAPTERLIST",
                      help="Selects which adapters returned by --list-adapters should "
                           "be affected by other atitweak options.  ADAPTERLIST contains "
                           "either a comma-seperated sequence of the index numbers of the "
                           "adapters to be affected or else contains the keyword \"all\" to "
                           "select all the adapters. If --adapter is missing, all adapters "
                           "will be affected.")
    
    parser.add_option("-P", "--performance-level", dest="plevel", default="all", 
                      metavar="PERFORMANCELEVELLIST",
                      help="Selects which performance levels returned by --list-adapters should be "
                           "affected by other atitweak options. PERFORMANCELEVELLIST contains either "
                           "a comma-separated sequence of the index numbers of the performance levels "
                           "to be affected or else contains the keyword \"all\" to select all "
                           "performance levels. If --performance-level is missing, all performance "
                           "levels will be affected.")
    
    (options, args) = parser.parse_args()

    if options.adapter_list == "all":
        adapter_list = None
    else:
        adapter_list = [int(adapter) for adapter in options.adapter_list.split(",")]

    if options.plevel == "all":
        plevel_list = None
    else:
        plevel_list = [int(plevel) for plevel in options.plevel.split(",")]

    result = 0
    
    try:
        initialize()
    
        if options.action == "list_adapters":
            list_adapters(adapter_list=adapter_list)
        elif options.action is None and (options.engine_clock or options.memory_clock or options.core_voltage):
            set_plevels(adapter_list=adapter_list,
                        plevel_list=plevel_list,
                        engine_clock=options.engine_clock,
                        memory_clock=options.memory_clock,
                        core_voltage=options.core_voltage)
        else:
            parser.print_help()
    
    except ADLError, err:
        result = 1
        print err
        
    finally:        
        shutdown()
        
    sys.exit(result)