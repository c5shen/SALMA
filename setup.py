#!/usr/bin/env python3
import os, sys, shutil, subprocess, time, signal
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
from argparse import ArgumentParser, Namespace
from platform import platform
from helpers.general_tools import executeBinary

_root_dir = os.path.dirname(os.path.realpath(__file__))
_config_path = os.path.join(_root_dir, 'default.config')

'''
4.11.2024 - helper function to notify users which binary files are
            having issues running (defined in main.config)
'''
def processExecutableOutput(section, item, binpath):
    out, returncode = executeBinary(binpath)
    b_err = 0

    # unnormal error & deal with mafft issue
    if not (returncode == 0 or returncode == 1) or 'v0.000' in out.stderr:
        print('\n\t[{}] {}: returncode={}'.format(section, item, returncode))
        print('\texecutable path:', binpath)
        print('\tstdout:', out.stdout.strip())
        print('\tstderr:', out.stderr.strip())
        print('\tERROR: binary not found or cannot run on your environment!\n')
        b_err = 1
    else:
        print('\t[{}] {}: returncode={}, success'.format(section, item, returncode))
    return b_err

def setup(prioritize_user_software, platform=platform()): 
    config_defaults = []
    cparser = configparser.ConfigParser()
    cparser.optionxform = str
    assert os.path.exists('{}'.format(_config_path)), \
            "default config file {} missing! Please redownload from Github\n".format(
                    _config_path)

    main_config_path = os.path.join(_root_dir, 'main.config')
    if os.path.exists(main_config_path):
        print('Main configuration file already exists: {}'.format(main_config_path))
        print('If you wish to regenerate configs, please delete the file above.')
        #ans = input('Do you wish to regenerate the file? [yes(y)/no(n)]:')
        #if ans != 'yes' and ans != 'y':
        with open(main_config_path, 'r') as f:
            cparser.read_file(f)
        return cparser

    print('\n')
    # initialize main config file using default config file
    default_config = configparser.ConfigParser()
    with open(_config_path, 'r') as f:
        default_config.read_file(f)
    for section in default_config.sections():
        cparser.add_section(section)
        for k, v in default_config[section].items():
            cparser.set(section, k, v)

    # if platform is linux then we just copy the default config file
    # as main.config
    set_sections = ['Basic', 'MAGUS']
    if 'macOS' not in platform:
        print('System is {}, using default config as main.config...'.format(
            platform))
        # use existing binaries from MAGUS subfolder (reduce redundancy of
        # duplicated binaries)
        _magus_tools_dir = os.path.join(_root_dir, 'tools', 'magus', 'tools') 
        for _section in set_sections:
            # mafftpath
            cparser.set(_section, 'mafftpath',
                    os.path.join(_magus_tools_dir, 'mafft', 'mafft'))
            # mclpath
            cparser.set(_section, 'mclpath',
                    os.path.join(_magus_tools_dir, 'mcl', 'bin', 'mcl'))
            # fasttreepath
            cparser.set(_section, 'fasttreepath',
                    os.path.join(_magus_tools_dir, 'fasttree', 'FastTreeMP'))
            # hmmer packages
            for hmmer_pkg in ['hmmsearch', 'hmmalign', 'hmmbuild']:
                cparser.set(_section, '{}path'.format(hmmer_pkg),
                        os.path.join(_magus_tools_dir, 'hmmer', hmmer_pkg))
    else:
        if 'x86' not in platform:
            print('Warning: system is not using x86 architecture.',
                    'Some softwares such as FastTreeMP need to be',
                    'self-provided. See {} [Basic] '.format(_config_path),
                    'section for more information.')
        print("System is {}, reconfiguring main.config...".format(platform))

        # configure MAGUS to use macOS compatible executables
        _macOS_dir = os.path.join(_root_dir, 'tools', 'macOS')

        binaries = os.popen('ls {}'.format(_macOS_dir)).read().split('\n')[:-1]
        for binary in binaries:
            path = os.path.join(_macOS_dir, binary)
            for _section in set_sections:
                if 'FastTreeMP' in path:
                    cparser.set(_section, 'fasttreepath', path)
                else:
                    cparser.set(_section, '{}path'.format(binary), path)

    # binaries from the user's environment will be used in priority
    # if they exist
    if prioritize_user_software:
        print('Detecting existing software from the user\'s environment...')
        software = ['mafft', 'mcl',  
                'hmmsearch', 'hmmalign', 'hmmbuild', 'FastTreeMP']
        for soft in software:
            print('\t{}: {}'.format(soft, shutil.which(soft)))
            for _section in set_sections:
                if shutil.which(soft):
                    if soft != 'FastTreeMP':
                        cparser.set(_section, '{}path'.format(soft),
                                shutil.which(soft))
                    else:
                        cparser.set(_section, 'fasttreepath',
                                shutil.which(soft))

    with open(main_config_path, 'w') as f:
        cparser.write(f)
    print('\n(Done) main.config written to {}'.format(main_config_path))
    print('If you would like to make manual changes, please directly edit {}'.format(
        main_config_path))
    return cparser

def main():
    parser = ArgumentParser()
    parser.add_argument('-c', '--configure', default=None,
            choices=['macOS', 'linux'], required=False,
            help='Specify which system the configuration file should resolve ' \
                 'to. This is an optional field and by default, the software ' \
                 'will resolve this automatically. Regardless, users can ' \
                 'specify either macOS (x86) or linux.')
    parser.add_argument('-p', '--prioritize-user-software', default="true",
            choices=['true', 'false'], required=False,
            help='Whether to prioritize using software in the user\'s ' \
                 'environment. default: true')
    args = parser.parse_args()
    
    configs = None
    if args.configure:
        configs = setup(args.prioritize_user_software == "true", args.configure) 
    else:
        configs = setup(args.prioritize_user_software == "true")

    '''
    4.11.2024 - Added post-setup check on softwares to see if they can run
    '''
    print('\nChecking if binary executables can run...')
    num_err = 0
    for _section in ['Basic', 'MAGUS']:
        for k, v in configs[_section].items():
            # invoke the binaries and check their return codes
            if 'path' in k:
                num_err += processExecutableOutput(_section, k, v)
    if num_err == 0:
        print('All executables ran successfully...')

    print('\nExiting EMMA configuration setup...')
    exit(num_err > 0)

if __name__ == "__main__":
    main()
