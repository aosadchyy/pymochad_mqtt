class X10Parser:    
    def parse_mochad_line(self, line):
        """
        Parse a raw line of output from mochad
        """
        # bail out unless it's an incoming RFSEC dmessage
        if line[15:23] == 'Rx RFSEC':

            # decode message. format is either:
            #09/22 15:39:07 Rx RFSEC Addr: 21:26:80 Func: Contact_alert_min...
            #     ~ or ~
            #09/22 15:39:07 Rx RFSEC Addr: 0x80 Func: Motion_alert_SP554A
            line_list = line.split(' ')
            """ Get D56D80 from Addr like: D5:6D:80, 
                Get 080 from Addr like: 0x80.
                Get 256180 from Addr like: 25:61:80"""

            addr = line_list[5].replace(':','').replace('x','')
          
            func = line_list[7]

            func_dict = self.decode_func(func)

            return addr, func_dict, 'security'

        elif line[15:20] == 'Rx RF':

            # decode RF message. format is:
            #   02/13 23:54:28 Rx RF HouseUnit: B1 Func: On
            line_list = line.split(' ')
            house_code = line_list[5]
            house_func = line_list[7].lower()

            return house_code, {'func': house_func}, 'button'

        return '', ''
    
    def decode_func(self, raw_func):
        """
        Decode the "Func:" parameter of an RFSEC message
        """
        MOTION_DOOR_WINDOW_SENSORS = ['DS10A', 'DS12A', 'MS10A', 'SP554A']
        SECURITY_REMOTES = ['KR10A', 'KR15A', 'SH624']
        func_list = raw_func.split('_')
        func_dict = dict()

        func_dict['device_type'] = func_list.pop()

        # set event_type and event_state for motion and door/window sensors
        if func_dict['device_type'] in MOTION_DOOR_WINDOW_SENSORS:
            func_dict['event_type'] = func_list[0].lower()
            func_dict['event_state'] = func_list[1].lower()
            i = 2
        elif func_dict['device_type'] in SECURITY_REMOTES:
            i = 0
        # bail out if we have an unknown device type
        else:
            raise Exception("Unknown device type in {}: {}".format(
                  raw_func, func_dict['device_type']))

        # crawl through rest of func parameters
        while i < len(func_list):
            # delay setting
            if func_list[i] == 'min' or func_list[i] == 'max':
                func_dict['delay'] = func_list[i]
            # tamper detection
            elif func_list[i] == 'tamper':
                func_dict['tamper'] = True
            # low battery
            elif func_list[i] == 'low':
                func_dict['low_battery'] = True
            # Home/Away switch on SP554A
            elif func_list[i] == 'Home' and func_list[i+1] == 'Away':
                func_dict['home_away'] = True
                # skip over 'Away' in func_list
                i += 1
            # Arm system
            elif func_list[i] == 'Arm' and i+1 == len(func_list):
                func_dict['command'] = 'arm'
            # Arm system in Home mode
            elif func_list[i] == 'Arm' and func_list[i+1] == 'Home':
                func_dict['command'] = 'arm_home'
                # skip over 'Home' in func_list
                i += 1
            # Arm system in Away mode
            elif func_list[i] == 'Arm' and func_list[i+1] == 'Away':
                func_dict['command'] = 'arm_away'
                # skip over 'Away' in func_list
                i += 1
            # Disarm system
            elif func_list[i] == 'Disarm':
                func_dict['command'] = 'disarm'
            # Panic
            elif func_list[i] == 'Panic':
                func_dict['command'] = 'panic'
            # Lights on
            elif func_list[i] == 'Lights' and func_list[i+1] == 'on':
                func_dict['command'] = 'lights_on'
                # skip ovedr 'On' in func_list
                i += 1
            # Lights off
            elif func_list[i] == 'Lights' and func_list[i+1] == 'off':
                func_dict['command'] = 'lights_off'
                # skip ovedr 'Off' in func_list
                i += 1
            # unknown
            else:
                raise Exception("Unknown func parameter in {}: {}".format(
                      raw_func, func_list[i]))

            i += 1

        return func_dict
