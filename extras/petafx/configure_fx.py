
# TODO:
# 1) what meaning does -DString=... have in defines?

# configure switches that currently work for fx
# --prefix=/work/helias/nest_install_nov --without-gsl --without-python --without-readline --without-pthread CC=mpifcc CXX=mpiFCC CFLAGS=-D_XPG6 CXXFLAGS='--alternative_tokens -O0 -D_XPG6'


import re
import sys
import os
import fileinput


# global variables controlling build process
CC = 'g++'
C = 'gcc'
LD= 'g++'

# compile flags
CFLAGS = '  -W -Wall -pedantic -Wno-long-long  -O2 '
CCFLAGS = '  -W -Wall -pedantic -Wno-long-long  -O2 '

LDFLAGS ='  -lcurses -lreadline -lpthread -L/usr/lib -lgsl -lgslcblas -lm	 '

LDLIBS = '-lm -lcurses'


# nest source directory
nest_src = '/home/zaytsev/src/nest/nest-2.0.0/__NEST_SOURCE'

# nest build directory
nest_build = '/home/zaytsev/src/nest/nest-2.0.0/__NEST_BUILD'

# data and dic directory
pkg_data_dir = '/usr/local/share/nest'
pkg_doc_dir = '/usr/local/share/doc/nest'

# install directory
install_dir = '/usr/local'

# append include path for config.h, debug.h, ...
CCFLAGS += " -I./include/ -I" + nest_src + "/include/ -I. -I" + nest_src + "/libltdl/" 
CFLAGS += " -I./include/ -I" + nest_src + "/include/ -I."

DEFINES =\
    ' -DPKGDATADIR=\\\"' + pkg_data_dir + '\\\"'\
    + ' -DPKGDOCDIR=\\\"' + pkg_doc_dir + '\\\"'\
    + ' -DPKGSOURCEDIR=\\\"' + nest_src + '\\\"'\
    + " -DString=stdstring"\
    + " -DSLI_MAJOR_REVISION=2"\
    + " -DSLI_MINOR_REVISION=0"\
    + " -DHAVE_CONFIG_H "

CCFLAGS += DEFINES
CFLAGS += DEFINES

def get_source_files(filename, filevar):
    """Extract source files from Makefile.am"""
    
    # regular expression to look for
    # search for variable name containing source files
    pattern_var = re.compile( filevar )

    f = fileinput.input(filename, inplace=False)

    files = ""
    start = False
 
    for line in f:
        if fileinput.isfirstline():
            sys.stderr.write('Started processing %s\n' % fileinput.filename())

        if start:
            if line != '\n':
                files += line
            else:
                start = False
      
        if pattern_var.match( line ):
            print "found source files in ", fileinput.filename(), "in line", fileinput.filelineno(), line

            # get right hand side
            sp = line.split('=')
            files += sp[1]
            start = True

    f.close()
    
    return files


def copy_to_build(sourcedir, filelist):
  """function to copy list of files into target dir"""
  map(lambda fn : os.system('cp -f ' + sourcedir + fn + ' ' + nest_build), filelist)


def find_and_copy_sources(srcdir, makefile_var_name):
    """find source files names in Makefile.am
    in directory srcdir
    specified by variable makefile_var_name
    return separate list for cc and h files
    copy files into build directory"""

    sources = get_source_files(srcdir + "Makefile.am", makefile_var_name)


    # patterns to find cc, h, and cpp files
    find_cc = re.compile('[\w]*\.cc|[\w]*\.cpp')
    find_c = re.compile('[\w]*\.c[^\w]')
    find_h = re.compile('[\w]*\.h')

    # split into h, cc, and cpp files
    cc_files = find_cc.findall(sources)
    c_files = find_c.findall(sources)
    h_files = find_h.findall(sources)

    # copy all source files of sli to build directory 
    copy_to_build(srcdir, cc_files)
    copy_to_build(srcdir, c_files)
    copy_to_build(srcdir, h_files)

    return h_files, cc_files, c_files


def get_object_from_source(filelist):
    """convert .c, .cc, or .cpp files into .o files"""
    ending_rule = re.compile("\.(cc|cpp|c)")
    
    return map(lambda fn : re.sub(ending_rule, ".o", fn), filelist)

 
class Makefile:
    def __init__(self, filename):
        self.filename = filename
        self.f = file(filename, 'wa')

        # define variables in Makefile
        self.f.write('CC=' + CC + '\n')
        self.f.write('C=' + C + '\n')
        self.f.write('LD=' + LD + '\n\n')
        self.f.write('CFLAGS=' + CFLAGS + '\n\n')
        self.f.write('CCFLAGS=' + CCFLAGS + '\n\n')
        self.f.write('LDFLAGS=' + LDFLAGS + '\n\n')
        self.f.write('LDLIBS=' + LDLIBS + '\n\n')
        self.f.write('\n\n')


    def close(self):
        # write make rules

        # rule for cpp -> o
        self.f.write('.cpp.o:\n')
        self.f.write('\t$(CC) $(CCFLAGS) -c $< -o $@\n')

        # rule for cc -> o
        self.f.write('.cc.o:\n')
        self.f.write('\t$(CC) $(CCFLAGS) -c $< -o $@\n')

        # rule for c -> o
        self.f.write('.c.o:\n')
        self.f.write('\t$(C) $(CFLAGS) -c $< -o $@\n')

        # clean
        self.f.write('.phony clean:\n')
        self.f.write('\trm -f *.o\n')
	self.f.write('\trm -f *.ti\n')
	self.f.write('\trm -f *.ii\n')

        self.f.close()


    def add_subtargets(self, target, subtargets):
        self.f.write(target + ': ' + subtargets + '\n\n\n')
        

    def add_target(self, target_dir, target_name, source_files):

        objs = get_object_from_source(source_files)
        objs = reduce(lambda x,y: x + ' ' + y, objs)

        self.f.write(target_name + '_obj=' + objs + '\n')
        self.f.write(target_dir + '/' + target_name + ': $(' + target_name + '_obj)\n')
        self.f.write('\t$(LD) $(LDFLAGS) ' + '$(' + target_name + '_obj) $(LDLIBS) -o ' + target_dir + '/' + target_name + '\n\n\n')


    def add_install(self, targetname, target_dir, filelist):

        self.f.write(targetname + ' :' + filelist + '\n')
	self.f.write('\tmkdir -p ' + target_dir + '\n')
        self.f.write('\tcp ' + filelist + ' ' + target_dir + '\n\n\n')


#------------------------------------------#
# copy all source files into one directory #
#------------------------------------------#


# sources for sli executable

# get libnestutil
libnestutil_h, libnestutil_cc, libnestutil_c = find_and_copy_sources(nest_src + "/libnestutil/",
                                                                     "libnestutil_la_SOURCES")

# get libpuresli
libpuresli_h, libpuresli_cc, libpuresli_c = find_and_copy_sources(nest_src + "/sli/",
                                                                  "libpuresli_la_SOURCES")

# get sli executable
sli_h, sli_cc, sli_c = find_and_copy_sources(nest_src + "/sli/",
                                             "sli_SOURCES")


# sources specific for nest executable

# get libmodelmodule
libmodelsmodule_h, libmodelsmodule_cc, libmodelsmodule_c = find_and_copy_sources(nest_src + "/models/",
                                                                                 "libmodelsmodule_la_SOURCES")

# get libprecisemodule
libprecisemodule_h, libprecisemodule_cc, libprecisemodule_c = find_and_copy_sources(nest_src + "/precise/",
                                                                                    "libprecisemodule_la_SOURCES")

# get libtopologymodule
libtopologymodule_h, libtopologymodule_cc, libtopologymodule_c = find_and_copy_sources(nest_src + "/topology/",
                                                                                       "libtopologymodule_la_SOURCES")

# check, if path exists
if os.access(nest_src + "/developer/", os.F_OK):
    # get developermodule
    libdevelopermodule_h, libdevelopermodule_cc, libdevelopermodule_c = find_and_copy_sources(nest_src + "/developer/",
                                                                                          "libdevelopermodule_la_SOURCES")
else:
    libdevelopermodule_h = libdevelopermodule_cc = libdevelopermodule_c = []



# get nestkernel
nestkernel_h, nestkernel_cc, nestkernel_c = find_and_copy_sources(nest_src + "/nestkernel/",
                                                                  "libnest_la_SOURCES")

# get librandom
librandom_h, librandom_cc, librandom_c = find_and_copy_sources(nest_src + "/librandom/",
                                                               "librandom_la_SOURCES")

# get libsli
libsli_h, libsli_cc, libsli_c = find_and_copy_sources(nest_src + "/sli/",
                                                      "libsli_base_sources")

# get nest executable sources
nest_h, nest_cc, nest_c = find_and_copy_sources(nest_src + "/nest/",
                                                "nest_SOURCES")

# write a new makefile
print "now writing Makefile_fx"

os.chdir(nest_build)

mk = Makefile("Makefile_fx")

# add main target 'all'
mk.add_subtargets("all", "sli/sli nest/nest")

# add target sli
mk.add_target("sli", "sli",\
              sli_cc + sli_c\
            + libpuresli_cc + libpuresli_c\
            + libnestutil_cc + libnestutil_c)

# add target nest
mk.add_target("nest", "nest",\
              nest_cc + nest_c\
            + libmodelsmodule_cc + libmodelsmodule_c\
            + libprecisemodule_cc + libprecisemodule_c\
            + libtopologymodule_cc + libtopologymodule_c\
            + libdevelopermodule_cc + libdevelopermodule_c\
            + nestkernel_cc + nestkernel_c\
            + librandom_cc + librandom_c\
            + libnestutil_cc + libnestutil_c\
            + libsli_cc + libsli_c)

# add install target
inst_tgts = "install_nest install_sli install_data"

# add for developer version
if libdevelopermodule_h != []:
    inst_tgts += " install_dev_data"

mk.add_subtargets("install", inst_tgts)
mk.add_install("install_sli", install_dir + "/bin", "./sli/sli")
mk.add_install("install_nest", install_dir + "/bin", "./nest/nest")
mk.add_install("install_data", pkg_data_dir + "/sli", nest_src + "/lib/sli/*.sli " + nest_src + "/topology/sli/*.sli " + nest_src + "/models/sli/*.sli")

# add for developer version
if libdevelopermodule_h != []:    
    mk.add_install("install_dev_data", pkg_data_dir + "/sli", nest_src + "/developer/sli/*.sli")

mk.close()

print "please next run:"
print "make -f Makefile_fx -j<number of make jobs>"
print "e.g."
print "make -f Makefile_fx -j8"
print "this may take a while"
print "finally run:"
print "make -f Makefile_fx install"
