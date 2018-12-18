#!/usr/bin/env python
# the purpose of this script is to parse a truss or strace log file and summarise all the commands
# e.g. on AIX generate a truss log file like this: truss -d -f -o truss.log -p <pid>
# e.g. on Linux generate a strace log file like this: strace -ttt -T -f -o strace.log -p <pid>
# default usage: python PerfTraceParser.py
#           or: python PerfTraceParser.py logfilename

import sys,time,traceback,math
from collections import OrderedDict

# globals
compare_field = ''
debug = False

class PrintFormat():
    def __init__(self):
        self.max_format = '5;30;41'
        self.nearmax_format = '5;30;43'
        self.nearmax_threshold = 0.5

    def set_max(self, key, value):
        if hasattr(self, key):
            # convert new value to int
            value = int(value)
            # get the previous value
            prev_value = int(getattr(self, key))
            # check if it is bigger
            if value > prev_value:
                # if it's bigger then update it
                setattr(self, key, value)
        else:
            # does not exist so set to what was passed in
            setattr(self, key, value)
        self.set_maxwidth(key, value)

    def get_max(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        else:
            # not set return 0
            return 0

    def set_maxwidth(self, key, value):
        value_length = len(str(value))
        maxwidth_key = 'maxwidth_' + key
        if hasattr(self, maxwidth_key):
            existing_maxwidth = getattr(self, maxwidth_key)
            if (value_length > existing_maxwidth):
                setattr(self, maxwidth_key, value_length)
        else:
            # not set, so set it
            setattr(self, maxwidth_key, value_length)

    def setget_maxwidth(self, key, value):
        value_length = len(str(value))
        self.set_maxwidth(key, value)
        maxwidth_key = 'maxwidth_' + key
        existing_maxwidth = getattr(self, maxwidth_key)
        return existing_maxwidth

    def fixed_width_print(self,print_string, width):
        space = ' '
        print_string = str(print_string)
        howmuch = width - len(print_string) if len(print_string) < width else 1
        return str('{0}{1}'.format(print_string, space * howmuch))

    def max_colour_print(self, value, maxvalue, width):
        if value == 0 or maxvalue == 0:
            colour = False
        elif value == maxvalue:
            colour = True
            format = self.max_format
        elif value >= (maxvalue * self.nearmax_threshold):
            colour = True
            format = self.nearmax_format
        else:
            colour = False
        value_formatted = self.fixed_width_print(value, width)        
        if colour == True:
            value_formatted = '\x1b[{0}m{1}\x1b[0m'.format(format, value_formatted)
        return value_formatted

def dict_inc_or_add(dict_to_check, key):
    if key in dict_to_check:
        dict_to_check[key] += 1
    else:
        dict_to_check[key] = 1

def print_dict(title, dict, output_limit = 10):
    print('Top {0} {1}:'.format(output_limit, title))
    i = 0
    #loop through a sorted representation of the dict by value and print out up until the limit
    for key in dict:
        i += 1
        print('{0}: {1}'.format(key, dict[key]), flush=True)
        if i >= output_limit:
            break
            
def sort_dict(unsorted_dict, descending_direction=True):
    # sort dict by value and direction
    sorted_dict = OrderedDict(sorted(unsorted_dict.items(), key=lambda k: k[1], reverse=descending_direction))
    return sorted_dict

class FileInstance():
    def __init__(self, filename, handle, print_format, file_commands):
        self.print_format = print_format
        self.file_commands = file_commands
        self.filename = filename
        self.print_format.set_maxwidth('filename', filename)
        self.lasthandle = handle
        self.print_format.set_maxwidth('handle', handle)
        self.handles = []
        self.file_exclusions = ['sig', 'sock', 'shutdown', 'connext', 'esend']

    def incHandles(self, handle):
        self.lasthandle = handle
        if handle not in self.handles and handle is not '0':
            self.handles.append(handle)

    def incAttr(self, key):
        # check for exclusion commands
        exclude = False
        if key in self.file_exclusions:
            exclude = True
        if exclude is not True:                
            new_value = 1
            # does it already exist?
            if hasattr(self, key):
                # get the previous value and increment it
                new_value = int(getattr(self, key)) + 1
            # udpate the value
            setattr(self, key, new_value)
            # update the max value for this key
            self.print_format.set_max(key, new_value)
            # add the key to list of file commands if not already added
            if key not in self.file_commands:
                self.file_commands.append(key)
        else:
            # this command is to be excluded
            pass
            
    def get_attr_val_safe(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        else:
            # not set return 0
            return 0
            
    def header(self):        
        output_string = ''        
        title_filename = 'filename'        
        width = self.print_format.setget_maxwidth(title_filename, title_filename) + 4        
        str_filename = self.print_format.fixed_width_print(title_filename, width)        
        output_string = '{0}'.format(str_filename)        
        title_lasthandle = 'handle'
        width = self.print_format.setget_maxwidth(title_lasthandle, title_lasthandle) + 2 
        str_lasthandle = self.print_format.fixed_width_print(title_lasthandle, width)
        output_string = '{0}|{1}'.format(output_string, str_lasthandle)        
        for command in self.file_commands:
            width = self.print_format.setget_maxwidth(command, command) + 2
            cmd_print = self.print_format.fixed_width_print(command, width)
            output_string = '{0}|{1}'.format(output_string, cmd_print)        
        str_handles = 'handles'
        output_string = '{0}|{1}'.format(output_string, str_handles)        
        underline = '-' * len(output_string)
        return output_string + '\n' + underline
        
    def __str__(self):        
        output_string = ''        
        title_filename = 'filename'        
        width = self.print_format.setget_maxwidth(title_filename, self.filename) + 4        
        str_filename = self.print_format.fixed_width_print(self.filename, width)        
        output_string = '{0}'.format(str_filename)        
        title_lasthandle = 'handle'
        width = self.print_format.setget_maxwidth('handle', str(self.lasthandle)) + 2 
        str_lasthandle = self.print_format.fixed_width_print(str(self.lasthandle), width)
        output_string = '{0}|{1}'.format(output_string, str_lasthandle)        
        for command in self.file_commands:            
            current_value = self.get_attr_val_safe(command)
            max_val = self.print_format.get_max(command)
            width = self.print_format.setget_maxwidth(command, current_value) + 2
            cmd_print = self.print_format.max_colour_print(current_value, max_val, width)
            output_string = '{0}|{1}'.format(output_string, cmd_print)
        output_string = '{0}|{1}'.format(output_string, self.handles)        
        return output_string
        
    def get_compare_values(self,other):
        global compare_field
        if isinstance(other, str):
            # Silently convert for comparison
            other = FileInstance(other, 0, self.print_format, self.file_commands)
        if not isinstance(other, FileInstance):
            raise TypeError("{0} is not of type FileInstance".format(type(other)))
        value_self = 0
        value_other = 0
        if compare_field is not '':
            if hasattr(self, compare_field):
                value_self = getattr(self, compare_field)
            if hasattr(other, compare_field):
                value_other = getattr(other, compare_field)
        else:
            value_self = getattr(self, 'filename')
            value_other = getattr(other, 'filename')
        return value_self, value_other

    def __lt__(self,other):
        value_self, value_other = self.get_compare_values(other)    
        return value_self < value_other

    def __eq__(self,other):
        value_self, value_other = self.get_compare_values(other)    
        return value_self == value_other
        
    def __gt__(self,other):
        value_self, value_other = self.get_compare_values(other)
        return value_self > value_other

class PerfTracerParser():
    def print_usage(self):
        print('')
    
    def __init__(self, logfile):
        self.lines = 0
        self.fd_limit = 1024
        self.early_stop = False
        self.output_limit = 10
        self.descending_direction = True
        self.filename_filter = ''
        self.associated_file_instances = []
        self.file_commands = []
        self.handles_and_files = dict()
        self.syscall_commands = dict()
        self.syscall_files = dict()
        self.syscall_semaphores = dict()
        self.syscall_handles = dict()
        self.syscall_memaddresses = dict()
        self.syscall_empty = dict()
        self.syscall_errors = dict()
        self.syscall_unknown = dict()
        self.logfile = logfile
        print('Log file is: \'{0}\''.format(self.logfile))
        self.print_format = PrintFormat()
        return
        
    def sort_dicts(self):
        self.syscall_commands = sort_dict(self.syscall_commands)
        self.syscall_files = sort_dict(self.syscall_files)
        self.syscall_semaphores = sort_dict(self.syscall_semaphores)
        self.syscall_handles = sort_dict(self.syscall_handles)
        self.syscall_memaddresses = sort_dict(self.syscall_memaddresses)
        self.syscall_empty = sort_dict(self.syscall_empty)
        self.syscall_errors = sort_dict(self.syscall_errors)
        self.syscall_unknown = sort_dict(self.syscall_unknown)
        return

    def print_summary(self, sort=False):
        if sort:
            self.sort_dicts()
        print('\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n')
        print('Total lines parsed: {0}'.format(self.lines))
        print('------------------------------')
        print_dict("commands", self.syscall_commands)
        print('------------------------------')
        print_dict("files referenced", self.syscall_files)
        print('------------------------------')
        print_dict("semaphores", self.syscall_semaphores)
        print('------------------------------')
        print_dict("handles", self.syscall_handles)
        print('------------------------------')
        print_dict("memory addresses references", self.syscall_memaddresses)
        print('------------------------------')
        print_dict("empty calls", self.syscall_empty)
        print('------------------------------')
        print_dict("errors", self.syscall_errors)
        print('------------------------------')
        print_dict("unknown", self.syscall_unknown)
        print('------------------------------')
        self.key_control('O'+ list(self.syscall_commands.keys())[0])
        print('\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n')
        return

    def user_input(self,prompt):
        try:
            input_chars = input(prompt)
            return input_chars
        except (KeyboardInterrupt, SystemExit):
            #Exititing
            print("Exiting")
            sys.exit(0)
        except:
            #print('Unexpected error: ', sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)
            raise

    def key_control(self, chars):
        global compare_field
        chars = chars[:1].upper() + chars[1:]
        if chars == 'L':
            try:
                self.output_limit = int(self.user_input('Enter a new limit: '))
            except:
                self.output_limit = 10
                print('Defulting to 10')
            else:
                print('New limit is -> {0}'.format(self.output_limit))
        elif chars == 'C':
            print_dict('Commands',self.syscall_commands)
        elif chars == 'A':
            print('Associated files = {0}'.format(len(self.associated_file_instances)))
            print('output limited to => {0}'.format(self.output_limit))
            print('filename filter is set to => \'{0}\''.format(self.filename_filter))
            print('Ordered by "{0}" in {1} order'.format('filename' if compare_field is '' else compare_field, 'descending' if self.descending_direction else 'ascending'))
            counter = 0
            print(FileInstance('', 0, self.print_format, self.file_commands).header())
            if self.descending_direction:
                output_array = reversed(sorted(self.associated_file_instances))
            else:
                output_array = sorted(self.associated_file_instances)
            # loop through the array
            for fileinstance in output_array:
                # text filter
                if self.filename_filter is not '':
                    if self.filename_filter.lower() not in fileinstance.filename.lower():
                        continue
                counter += 1
                if counter > self.output_limit:
                    continue
                else:
                    print(fileinstance)
            if self.filename_filter is not '':
                print("{0} entries match the filter".format(counter))
        elif chars[:1] == 'F':
            if chars == 'F':
                #reset the sort, which will default to filenames
                self.filename_filter = ''
                print('Enter keyword to search for and filter associated files with: ')
                self.key_control('F' + self.user_input(''))
            elif chars == 'F ':
                self.filename_filter = ''
                self.key_control('A')
            else:
                try:
                    # has the user entered blank
                    print(chars[1:])
                    text_selection = chars[1:]
                    self.filename_filter = text_selection
                    self.key_control('A')                        
                except:
                    print('Error, please type something valid')
                    self.key_control('F')
        elif chars[:1] == 'O':
            if chars == 'O':
                #reset the sort, which will default to filenames
                compare_field = ''
                print('Sort associated files by field: ')
                index = 1
                for command in self.file_commands:                
                    print('[{0}] {1}'.format(index, command))
                    index += 1
                self.key_control('O'+ self.user_input(''))
            else:
                # check for a number
                # selection
                try:
                    # has the user entered blank
                    print(chars[1:])
                    text_selection = chars[1:]                        
                    if text_selection is '':
                        # default to filename
                        compare_field = 'filename'
                    else:
                        if text_selection in self.file_commands:
                            compare_field = text_selection
                        else:
                            int_selection = int(text_selection)
                            index = 1
                            compare_field = ''
                            for command in self.file_commands:
                                if int_selection == index:
                                    compare_field = command
                                    print('[{0}] {1}'.format(index, command))
                                    break
                                index += 1
                            if compare_field == '':
                                raise
                    # if it got this far then just print the file association
                    self.key_control('A')
                except:
                    print('Error, please choose a valid field')
                    self.key_control('O')
        elif chars == 'Q':
            print('BYE!')
            sys.exit(0)
        elif chars == 'S':
            self.print_summary(False)
        elif chars == 'R':
            self.descending_direction = not self.descending_direction
            print('Output direction will be ' + ('descending' if self.descending_direction is True else 'ascending')) 
            self.print_summary(True)
        return

    def show_options(self):
        while True:
            print('============================================================')
            print('[C] Show top {0} commands'.format(self.output_limit))
            print('[A] Show associated files')
            print('[O] Order associated files by field')
            print('[F] Filter on filenames')
            print('[S] Print the summary')
            print('[R] Reverse the output direction')
            print('[L] Change output limit, currently set to "{0}"'.format(self.output_limit))
            print('[Q] Quit')
            print('============================================================')
            self.key_control(self.user_input(''))
        return

    def startTimer(self):
        self.stopwatch = time.time()
        
    def stopTimer(self):
        self.stopwatch = time.time() - self.stopwatch

    def printTimer(self):
        print("Time taken: {0:.3} seconds".format(self.stopwatch), flush=True)
        
    def fileLength(self):
        iLines = 0
        with open(self.logfile) as fp:
            iLines = sum(1 for _ in fp)
        self.total_lines = iLines

    def parse_log_file(self):
        global debug
        # read the file to get line count and save in globals
        if debug:
            print("Checking file length")
            self.startTimer()
        self.fileLength()
        if debug:
            self.stopTimer()        
            self.printTimer()
        print("Parsing trace log...")
        with open(self.logfile) as fp:            
            for line_no, line in enumerate(fp,1):
                if self.early_stop == True:
                    print("stopping parsing", flush=True)
                    break
                found_command = False
                progressPerc = int((self.lines / self.total_lines) * 100)
                try:
                    # debug the timing
                    if debug == True:
                        if self.lines % 1000 == 0:
                            self.stopTimer()                        
                            print('processed {0} lines so far in {1:.3} sseconds'.format(self.lines, self.stopwatch) +
                                    '\nAssociated Files so far: {0}'.format(len(self.associated_file_instances)) +
                                    '\nFiles mentioned: {0}'.format(len(self.handles_and_files)), flush=True)
                            self.startTimer()
                    # new way of showing progress
                    # point = self.total_lines / 100
                    # increment = round(self.total_lines / 20)                    
                    # progressPerc = round((self.lines / self.total_lines) * 100,2)
                    # if int(progressPerc)>0 and int(progressPerc) % 5 == 0:
                       # sys.stdout.write('\r processing: <{0:=<20}>{1:2.2f}%'.format("*"*int(progressPerc/10),progressPerc))
                       # sys.stdout.flush()
                    line = line.rstrip()
                    self.lines += 1
                    if line_no == 1 and "Trace Started" in line:
                        continue
                    progressPerc = round((self.lines / self.total_lines) * 100)
                    increment = self.total_lines / 20
                    if (self.lines % int(increment) == 0) or (self.lines == self.total_lines):
                        sys.stdout.write("\r[{0}{1}] line {2} of {3} lines = {4}%".format("="*int(self.lines/increment)," "*int((self.total_lines-self.lines)/increment), self.lines, self.total_lines, progressPerc))
                        sys.stdout.flush()
                    # grab the first bit of the string up till the open bracket
                    syscall_command = line.split("(")[0]
                    # now remove the first part of the string until the last space
                    syscall_command = syscall_command[syscall_command.rfind(' ')+1:].strip()
                    # what remains should be the command
                    dict_inc_or_add(self.syscall_commands, syscall_command)
                    found_file = 0
                    firstparam = ""
                    filehandle = 0
                    # try to get a filename
                    #grab everything after the first open bracket
                    try:
                        firstparam = line.split("(")[1]                       

                    except Exception as e:
                        # first line is sometimes incomplete
                        if line_no > 1:
                            print('error processing line <', self.lines, '> of file <', self.logfile,'>')
                            print(line)
                            #print(sys.exc_info())
                            #print(e)
                            traceback.print_exc(file=sys.stdout)
                            sys.exit(1)
                    # now grab everything before the first comma, if there is one
                    if "," in firstparam:
                        firstparam = firstparam.split(",")[0]
                    if "\"" in firstparam:
                        filename = firstparam.split("\"")[1]                        
                        dict_inc_or_add(self.syscall_files, filename)
                        # what do we want to track about this particular system call
                        attr_key = ''
                        #first make sure the command did not error
                        if "Err#" not in line and "= -" not in line:
                            # if there is a filename then there could be a handle at the end...
                            filehandle = line[line.rfind('=')+1:].strip()
                            if filehandle == 0:
                                # command was executed with success
                                attr_key = 'success'
                                attr_value = 1
                            elif filehandle == -1:
                                # command was executed with failure                                
                                attr_key = 'failure'
                                attr_value = 1
                            else:
                                # this is probably statx or kopen giving us a handle...
                                attr_key = 'handle'
                                attr_value = filehandle
                        else:
                            # there is an error add it to the dict
                            if line.rfind('Err#') > -1:
                                error_text = line[line.rfind('Err#'):].strip()
                            else:
                                error_text = line[line.rfind('= -')+1:].strip()
                            dict_inc_or_add(self.syscall_errors,error_text)
                            # command was executed with failure
                            attr_key = 'error'
                            attr_value = error_text
                        # update the file's handle in our list
                        self.handles_and_files[filehandle] = filename
                        # now look for the file in the list and either 
                        # update the attribute
                        try:
                            index = self.associated_file_instances.index(filename)
                            if index in range(0,len(self.associated_file_instances)):
                                found_file = True
                                fileinstance = self.associated_file_instances[index]
                                # update the key value pair with the system call that was executed
                                fileinstance.incAttr(syscall_command)
                                # update the key value pair with the result of the system call
                                if attr_key == 'handle':
                                    fileinstance.incHandles(filehandle)
                                fileinstance.incAttr(attr_key)
                        except (KeyboardInterrupt, SystemExit):
                            self.early_stop = True
                        except ValueError:
                            pass
                        except Exception as error:
                            print("Error checking the file instance {0}".format(repr(error)))
                        # the file is not in our list
                        if found_file == 0:
                            # create a file instance with the handle as 0
                            file_instance = FileInstance(filename, 0, self.print_format, self.file_commands)
                            file_instance.incAttr(syscall_command)
                            # update the key value pair with the result of the system call
                            if attr_key == 'handle':
                                file_instance.incHandles(filehandle)
                            else:
                                file_instance.incAttr(attr_key)                            
                            self.associated_file_instances.append(file_instance)                        
                    else:
                        if "Err#" in line or "= -" in line:
                            # there is an error add it to the dict
                            if line.rfind('Err#') > -1:
                                error_text = line[line.rfind('Err#'):].strip()
                            else:
                                error_text = line[line.rfind('= -')+1:].strip()
                            dict_inc_or_add(self.syscall_errors,error_text)
                        # no file probably a handle
                        if "," in line:
                            address = line.split("(")[1].split(",")[0]
                        else:
                            # look for the close bracket
                            address = line.split("(")[1].split(")")[0]
                        if address == "":
                            # empty params passed in, count them seperately
                            dict_inc_or_add(self.syscall_empty,syscall_command)
                        else:
                            # is it a memory address or a handle
                            if address[:2] == "0x":
                                # for the counter we only count by handle number
                                dict_inc_or_add(self.syscall_memaddresses, address)
                            else:
                                try:
                                    if int(address) > self.fd_limit:
                                        dict_inc_or_add(self.syscall_semaphores, address)
                                    else:
                                        dict_inc_or_add(self.syscall_handles, address)
                                        file_found = False
                                        file_instance_found = False
                                        if address in self.handles_and_files:
                                            filename = self.handles_and_files[address]
                                            file_found = True
                                            # we have a filename!
                                            # let's add the system call to it's collections
                                            # fetch the instance from our list
                                            try:
                                                index = self.associated_file_instances.index(filename)
                                                if index in range(0,len(self.associated_file_instances)):
                                                    file_instance_found = True
                                                    # update the key value pair with the system call that was executed
                                                    self.associated_file_instances[index].incAttr(syscall_command)
                                            except ValueError:
                                                pass
                                            except Exception as error:
                                                print("Error checking the file instance {0}".format(repr(error)))
                                        if not file_found and not file_instance_found:
                                            # not in our associated files, we don't know where to put to return add it to the unknown.
                                            dict_inc_or_add(self.syscall_unknown, syscall_command)
                                except KeyboardInterrupt:
                                    self.early_stop = True
                                except:
                                    # non number...
                                    dict_inc_or_add(self.syscall_unknown, syscall_command)
                except (KeyboardInterrupt, SystemExit):
                    self.early_stop = True
                except Exception as e:
                    # first line is sometimes incomplete
                    if line_no > 1:
                        print('error processing line <', self.lines, '> of file <', self.logfile,'>')
                        print(line)
                        #print(sys.exc_info())
                        #print(e)
                        traceback.print_exc(file=sys.stdout)
                        sys.exit(1)
            print("\nFinished parsing trace log!\n\n")

    def main(self):
        self.parse_log_file()
        self.print_summary(True)
        # open menu in continuous loop
        self.show_options()

if __name__=='__main__':
    try:
        logfile = sys.argv[1].strip()
    except:
        print('no log specified defaulting to trace.log')
        logfile = 'trace.log'
    try:
        if sys.argv[2].strip() == "debug":
            debug = True
    except:
        debug = False
    app = PerfTracerParser(logfile)
    app.main()
