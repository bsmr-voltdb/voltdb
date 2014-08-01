#!/usr/bin/env python

# This file is part of VoltDB.
# Copyright (C) 2008-2014 VoltDB Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with VoltDB.  If not, see <http://www.gnu.org/licenses/>.

"""
VoltDB catalog code generator.
"""

from catalog_utils import *
from string import Template
from subprocess import Popen

#
# Code generation (shared).
#

def writer( f ):
    def write( *args ):
        f.write( ' '.join( map( str, args ) ) + '\n' )
    return write

def interp(text, params = locals()):
    t = Template(text)
    #return t.safe_substitute(params)
    return t.substitute(params)

#
# Java code generation.
#

def javatypify( x ):
    if x == 'string': return 'String'
    elif x == 'int': return 'int'
    elif x == 'bool': return 'boolean'
    elif x[-1] == '*': return 'CatalogMap<%s>' % x.rstrip('*')
    elif x[-1] == '?': return x.rstrip('?')
    else: raise Exception( 'bad type: ' + x )

def javaobjectify( x ):
    if x == 'string': return 'String'
    elif x == 'int': return 'Integer'
    elif x == 'bool': return 'Boolean'
    elif x[-1] == '*': return 'CatalogMap<%s>' % x.rstrip('*')
    elif x[-1] == '?': return x.rstrip('?')
    else: raise Exception( 'bad type: ' + x )

def genjava( classes, prepath, postpath, package ):
    ##########
    # SETUP
    ##########
    pkgdir = package.replace('.', '/')
    os.system( interp( "rm -rf $postpath/*", locals() ) )
    os.system( interp( "mkdir -p $postpath/", locals() ) )
    os.system( interp( "cp $prepath/Catalog.java $postpath", locals() ) )
    os.system( interp( "cp $prepath/CatalogType.java $postpath", locals() ) )
    os.system( interp( "cp $prepath/CatalogMap.java $postpath", locals() ) )
    os.system( interp( "cp $prepath/CatalogException.java $postpath", locals() ) )
    os.system( interp( "cp $prepath/CatalogChangeGroup.java $postpath", locals() ) )
    os.system( interp( "cp $prepath/CatalogDiffEngine.java $postpath", locals() ) )
    os.system( interp( "cp $prepath/FilteredCatalogDiffEngine.java $postpath", locals() ) )

    ##########
    # WRITE THE SOURCE FILES
    ##########

    for cls in classes:
        clsname = cls.name
        javapath = postpath + "/" + clsname + '.java'
        #ensure_relative_path_exists(postpath + "/" + pkgdir)
        f = file( javapath, 'w' )
        if not f:
            raise OSError("Can't create file %s for writing" % javapath)
        write = writer( f )
        write (gpl_header)
        write (auto_gen_warning)
        write('package', package + ';\n')

        if cls.has_comment():
            write('/**\n *', cls.comment)
            write(' */')

        write( interp( 'public class $clsname extends CatalogType {\n', locals() ) )

        # fields
        for field in cls.fields:
            ftype = javatypify( field.type )
            fname = field.name
            #realtype = field.type[:-1]
            #methname = fname.capitalize()
            if ftype == "String":
                write( interp( '    String m_$fname = new String();', locals() ) )
            elif field.type[-1] == '?':
                write( interp( '    Catalog.CatalogReference<$ftype> m_$fname = new CatalogReference<>();', locals() ) )
            else:
                write( interp( '    $ftype m_$fname;', locals() ) )
        write( '' )

        # setBaseValues
        write( '    void setBaseValues(CatalogMap<? extends CatalogType> parentMap, String name) {' )
        write( '        super.setBaseValues(parentMap, name);')
        for field in cls.fields:
            ftype = javatypify( field.type )
            fname = field.name
            realtype = field.type[:-1]
            #methname = fname.capitalize()
            if field.type[-1] == '*':
                write( interp( '        m_$fname = new $ftype(getCatalog(), this, "$fname", $realtype.class, m_parentMap.m_depth + 1);', locals() ) )
        write( '    }\n' )

        # getFields
        write(                        '    public String[] getFields() {' )
        write(                        '        return new String[] {' )
        for field in cls.fields:
            if field.type[-1] != '*':
                fname = field.name
                write( interp(        '            "$fname",', locals() ) )
        write(                        '        };' )
        write(                        '    };\n' )

        # getChildCollections;
        write(                        '    String[] getChildCollections() {' )
        write(                        '        return new String[] {' )
        for field in cls.fields:
            if field.type[-1] == '*':
                fname = field.name
                write( interp(        '            "$fname",', locals() ) )
        write(                        '        };' )
        write(                        '    };\n' )


        #getField
        write(             '    public Object getField(String field) {' )
        write(             '        switch (field) {' )
        for field in cls.fields:
            fname = field.name
            methname = fname.capitalize()
            write( interp( '        case "$fname":', locals() ) )
            write( interp( '            return get$methname();', locals() ) )
        write( interp(     '        default:', locals() ) )
        write( interp(     '            throw new CatalogException("Unknown field");', locals() ) )
        write(             '        }' )
        write(             '    }\n' )

        # getter methods
        for field in cls.fields:
            ftype = javatypify( field.type )
            fname = field.name
            realtype = field.type[:-1]
            methname = fname.capitalize()
            if field.has_comment():
                write('    /** GETTER:', field.comment, '*/')
            write( interp( '    public $ftype get$methname() {', locals() ) )
            if field.type[-1] == '?':
                write( interp( '        return m_$fname.get();', locals() ) )
            else:
                write( interp( '        return m_$fname;', locals() ) )
            write( '    }\n' )

        # setter methods
        for field in cls.fields:
            ftype = javatypify( field.type )
            fname = field.name
            realtype = field.type[:-1]
            methname = fname.capitalize()
            if field.type[-1] == '*':
                continue
            if field.has_comment():
                write('    /** SETTER:', field.comment, '*/')
            write( interp( '    public void set$methname($ftype value) {', locals() ) )
            if field.type[-1] == '?':
                write( interp( '        m_$fname.set(value);', locals() ) )
            else:
                write( interp( '        m_$fname = value;', locals() ) )
            write( '    }\n' )

        # set
        write(                     '    @Override' )
        write(                     '    void set(String field, String value) {' ) 
        write(                     '        if ((field == null) || (value == null)) {' )
        write(                     '            throw new CatalogException("Null value where it shouldn\'t be.");' )
        write(                     '        }\n' )

        write(                     '        switch (field) {' )
        for field in cls.fields:
            if field.type[-1] == '*':
                # skip child collections for set
                continue
            fname = field.name
            ftype = javatypify( field.type )
            write( interp(         '        case "$fname":', locals() ) )
            if field.type[-1] == '?':
                write(             '            value = value.trim();' )
                write(             '            if (value.startsWith("null")) value = null;' )
                write(             '            assert((value == null) || value.startsWith("/"));' )
                write( interp(     '            m_$fname.setUnresolved(value);', locals() ) )
            elif ftype == "int":
                write(             '            assert(value != null);' )
                write( interp(     '            m_$fname = Integer.parseInt(value);', locals() ) )
            elif ftype == "boolean":
                write(             '            assert(value != null);' )
                write( interp(     '            m_$fname = Boolean.parseBoolean(value);', locals() ) )
            elif ftype == "String":
                write(             '            value = value.trim();' )
                write(             '            if (value.startsWith("null")) value = null;' )
                write(             '            if (value != null) {')
                write(             '                assert(value.startsWith("\\"") && value.endsWith("\\""));' )
                write(             '                value = value.substring(1, value.length() - 1);' )
                write(             '            }' )
                write( interp(     '            m_$fname = value;', locals() ) )
            write(                 '            break;' )
        write( interp(             '        default:', locals() ) )
        write( interp(             '            throw new CatalogException("Unknown field");', locals() ) )
        write(                     '        }' )
        write(                     '    }\n' )

        # copyFields
        write(                     '    @Override' )
        write(                     '    void copyFields(CatalogType obj) {' ) 
        if len(cls.fields) > 0:
            write(                 '        // this is safe from the caller' )
            write( interp(         '        $clsname other = ($clsname) obj;\n', locals() ) )
            for field in cls.fields:
                ftype = javatypify( field.type )
                fname = field.name
                if ftype in ["int", "boolean", "String"]:
                    write( interp( '        other.m_$fname = m_$fname;', locals() ) )
                elif field.type[-1] == '?':
                    write( interp( '        other.m_$fname.setUnresolved(m_$fname.getPath());', locals() ) )
                elif field.type[-1] == '*':
                    write( interp( '        other.m_$fname.copyFrom(m_$fname);', locals() ) )
        write(                     '    }\n' )

        # equals
        write(             '    public boolean equals(Object obj) {' )
        write(             '        // this isn\'t really the convention for null handling' )
        write(             '        if ((obj == null) || (obj.getClass().equals(getClass()) == false))' )
        write(             '            return false;\n' )

        write(             '        // Do the identity check' )
        write(             '        if (obj == this)' )
        write(             '            return true;\n' )

        write(             '        // this is safe because of the class check' )
        write(             '        // it is also known that the childCollections var will be the same' )
        write(             '        //  from the class check' )
        write( interp(     '        $clsname other = ($clsname) obj;\n', locals() ) )

        write(             '        // are the fields / children the same? (deep compare)' )
        for field in cls.fields:
            ftype = javatypify( field.type )
            fname = field.name
            if ftype in ["int", "boolean"]:
                write( interp( '        if (m_$fname != other.m_$fname) return false;', locals() ) )
            else:
                write( interp( '        if ((m_$fname == null) != (other.m_$fname == null)) return false;', locals() ) )
                write( interp( '        if ((m_$fname != null) && !m_$fname.equals(other.m_$fname)) return false;', locals() ) )
        write('')

        write(             '        return true;' )
        write(             '    }\n' )

        # wrap up
        write( '}' )

#
# C++ code generation.
#

def cpptypify( x ):
    if x == 'string': return 'std::string'
    elif x == 'int': return 'int32_t'
    elif x == 'bool': return 'bool'
    elif x[-1] == '*': return 'CatalogMap<%s>' % x.rstrip('*')
    elif x[-1] == '?': return 'CatalogType*'
    else: raise Exception( 'bad type: ' + x )

def gencpp( classes, prepath, postpath ):
    ##########
    # SETUP
    ##########
    os.system( interp( "rm -rf $postpath/*", locals() ) )
    os.system( interp( "mkdir -p $postpath/", locals() ) )
    os.system( interp( "cp $prepath/catalog.h $postpath", locals() ) )
    os.system( interp( "cp $prepath/catalogtype.h $postpath", locals() ) )
    os.system( interp( "cp $prepath/catalogmap.h $postpath", locals() ) )
    os.system( interp( "cp $prepath/catalog.cpp $postpath", locals() ) )
    os.system( interp( "cp $prepath/catalogtype.cpp $postpath", locals() ) )

    ##########
    # WRITE THE SOURCE FILES
    ##########
    for cls in reversed( classes ):
        clsname = cls.name

        referencedClasses = []
        for field in cls.fields:
            classType = field.type[:-1]
            if (field.type[-1] == "*") or (field.type[-1] == '?'):
                if classType not in referencedClasses:
                    referencedClasses.append(classType)
        if cls.name in referencedClasses:
            referencedClasses.remove(cls.name)

        ##########
        # WRITE THE HEADER FILE
        ##########

        f = file( postpath + "/" + clsname.lower() + ".h", 'w' )
        write = writer( f )

        write (gpl_header)
        write (auto_gen_warning)
        pp_unique_str = "CATALOG_" + clsname.upper() + "_H_"
        write("#ifndef", pp_unique_str);
        write("#define", pp_unique_str);
        write("")

        write('#include <string>')
        write('#include "catalogtype.h"')
        write('#include "catalogmap.h"\n')
        write('namespace catalog {\n')

        for classType in referencedClasses:
            write("class " + classType + ";")

        if cls.has_comment():
            write('/**\n *', cls.comment)
            write(' */')

        write( interp( 'class $clsname : public CatalogType {', locals() ) )
        write( '    friend class Catalog;' )
        write( interp( '    friend class CatalogMap<$clsname>;', locals() ) )

        # protected section
        write( '\nprotected:')

        # constructor
        write( '    ' + clsname + '(Catalog * catalog, CatalogType * parent, const std::string &path, const std::string &name);' )

        # Field Member variables.
        for field in cls.fields:
            ftype = cpptypify( field.type )
            privname = 'm_' + field.name
            write( interp( '    $ftype $privname;', locals() ) )

        # update method
        write("\n    virtual void update();\n")

        # add method
        write("    virtual CatalogType * addChild(const std::string &collectionName, const std::string &name);")

        # getChild method
        write("    virtual CatalogType * getChild(const std::string &collectionName, const std::string &childName) const;")

        # removeChild method
        write("    virtual bool removeChild(const std::string &collectionName, const std::string &childName);")

        # public section
        write("\npublic:")

        # destructor
        write('    ~' + clsname + '();\n');

        # getter methods
        for field in cls.fields:
            ftype = cpptypify( field.type )
            privname = 'm_' + field.name
            pubname = field.name
            Pubname = pubname.capitalize()
            if field.has_comment():
                write('    /** GETTER:', field.comment, '*/')
            if field.type == 'string':
                write ( interp( '    const std::string & $pubname() const;', locals() ) )
            elif field.type[-1] == '?':
                write ( "    const " + field.type[:-1] + " * " + pubname + "() const;")
            elif field.type[-1] == '*':
                write ( interp( '    const $ftype & $pubname() const;', locals() ) )
            else:
                write ( interp( '    $ftype $pubname() const;', locals() ) )

        write( '};\n' )

        write( '} // namespace catalog\n' )

        write ("#endif // ", pp_unique_str)

        ##########
        # WRITE THE CPP FILE
        ##########

        f = file( postpath + "/" + clsname.lower() + ".cpp", 'w' )
        write = writer( f )

        write (gpl_header)
        write (auto_gen_warning)
        filename = clsname.lower()
        write ( '#include <cassert>' )
        write ( interp( '#include "$filename.h"', locals() ) )
        write ( '#include "catalog.h"' )
        otherhdrs = ['#include "%s.h"' % field.type[:-1].lower() for field in cls.fields if field.type[-1] in ['*', '?'] ]
        uniques = {}
        for hdr in otherhdrs:
            uniques[hdr] = hdr
        for hdr in uniques.keys():
            write( hdr )
        write ( '\nusing namespace catalog;' )
        write ( 'using namespace std;\n' )

        # write the constructor
        mapcons = ["m_%s(catalog)" % field.name for field in cls.fields if field.type[-1] == '*']
        write ( interp( '$clsname::$clsname(Catalog *catalog, CatalogType *parent, const string &path, const string &name)', locals() ) )
        comma = ''
        if len(mapcons): comma = ','
        write ( interp( ': CatalogType(catalog, parent, path, name)$comma', locals()))

        mapcons = ["m_%s(catalog, this, path + \"/\" + \"%s\")" % (field.name, field.name) for field in cls.fields if field.type[-1] == '*']
        if len(mapcons) > 0:
            write( "  " + ", ".join(mapcons))
        write('{')

        # init the fields and childCollections
        write( '    CatalogValue value;' )
        for field in cls.fields:
            ftype = cpptypify( field.type )
            privname = 'm_' + field.name
            pubname = field.name
            if field.type[-1] == '*':
                write( interp( '    m_childCollections["$pubname"] = &$privname;', locals() ) )
            else:
                write( interp( '    m_fields["$pubname"] = value;', locals() ) )
        write ( "}\n" )

        # write the destructor
        write(clsname + '::~' + clsname + '() {');
        for field in cls.fields:
            if field.type[-1] == '*':
                ftype = field.type.rstrip('*')
                itr = ftype.lower() + '_iter'
                privname = 'm_' + field.name
                tab = '   '
                write(interp('$tab std::map<std::string, $ftype*>::const_iterator $itr = $privname.begin();', locals()))
                write(interp('$tab while ($itr != $privname.end()) {', locals()))
                write(interp('$tab $tab delete $itr->second;', locals()))
                write(interp('$tab $tab $itr++;', locals()))
                write(interp('$tab }', locals()))
                write(interp('$tab $privname.clear();\n', locals()))
        write('}\n')

        # write update()
        write ( interp( 'void $clsname::update() {', locals() ) )
        for field in cls.fields:
            ftype = cpptypify( field.type )
            privname = 'm_' + field.name
            pubname = field.name
            if field.type[-1] == '?':
                ext = "typeValue"
                write( interp( '    $privname = m_fields["$pubname"].$ext;', locals() ) )
            elif field.type[-1] != '*':
                ext = "intValue"
                if (ftype == 'std::string'):
                    ext = "strValue.c_str()"
                write( interp( '    $privname = m_fields["$pubname"].$ext;', locals() ) )
        write ( "}\n" )

        # write add(...)
        write ( interp( 'CatalogType * $clsname::addChild(const std::string &collectionName, const std::string &childName) {', locals() ) )
        for field in cls.fields:
            if field.type[-1] == "*":
                privname = 'm_' + field.name
                pubname = field.name
                write ( interp( '    if (collectionName.compare("$pubname") == 0) {', locals() ) )
                write ( interp( '        CatalogType *exists = $privname.get(childName);', locals() ) )
                write ( '        if (exists)\n            return NULL;' )
                write ( interp( '        return $privname.add(childName);\n    }', locals() ) )
        write ( '    return NULL;\n}\n' )

        # write getChild(...)
        write ( interp( 'CatalogType * $clsname::getChild(const std::string &collectionName, const std::string &childName) const {', locals() ) )
        for field in cls.fields:
            if field.type[-1] == "*":
                privname = 'm_' + field.name
                pubname = field.name
                write ( interp( '    if (collectionName.compare("$pubname") == 0)', locals() ) )
                write ( interp( '        return $privname.get(childName);', locals() ) )
        write ( '    return NULL;\n}\n' )

        # write removeChild(...)
        write ( interp( 'bool $clsname::removeChild(const std::string &collectionName, const std::string &childName) {', locals() ) )
        write ( interp( '    assert (m_childCollections.find(collectionName) != m_childCollections.end());', locals() ) )
        for field in cls.fields:
            if field.type[-1] == "*":
                privname = 'm_' + field.name
                pubname = field.name
                write ( interp( '    if (collectionName.compare("$pubname") == 0) {', locals() ) )
                write ( interp( '        return $privname.remove(childName);', locals() ) )
                write ( interp( '    }', locals() ) )
        write ( interp( '    return false;', locals() ) )
        write ( '}\n' )

        # write field getters
        for field in cls.fields:
            ftype = cpptypify( field.type )
            privname = 'm_' + field.name
            pubname = field.name
            outertype = field.type[:-1]
            if field.type == 'string':
                write ( interp( 'const string & $clsname::$pubname() const {\n    return $privname;\n}\n', locals() ) )
            elif field.type[-1] == '?':
                write ( interp( 'const $outertype * $clsname::$pubname() const {', locals() ) )
                write ( interp( '    return dynamic_cast<$outertype*>($privname);\n}\n', locals() ) )
            elif field.type[-1] == '*':
                write ( interp( 'const $ftype & $clsname::$pubname() const {\n    return $privname;\n}\n', locals() ) )
            else:
                write ( interp( '$ftype $clsname::$pubname() const {\n    return $privname;\n}\n', locals() ) )

#
# Main.
#

def main():
    specpath = "spec.txt"
    javapkg = 'org.voltdb.catalog'
    cpp_postpath = 'out/cppsrc'
    cpp_prepath = 'in/cppsrc'
    java_prepath = 'in/javasrc'
    java_postpath = 'out/javasrc'
    f =  file( specpath )
    classes = parse( f.read() )
    genjava( classes, java_prepath, java_postpath, javapkg )
    gencpp( classes, cpp_prepath, cpp_postpath )

main()
