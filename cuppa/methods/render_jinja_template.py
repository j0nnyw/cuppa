
#          Copyright Jamie Allsop 2022-2022
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE_1_0.txt or copy at
#          http://www.boost.org/LICENSE_1_0.txt)

#-------------------------------------------------------------------------------
#   RenderJinjaTemplateMethod
#-------------------------------------------------------------------------------

import json
import cuppa.progress
from cuppa.log import logger
from cuppa.colourise import as_notice, colour_items


class RenderTemplateAction(object):

    def __init__( self, base_path, variables ):
        self._base_path = base_path
        self._variables = variables or {}
        if self._variables:
            logger.debug( "storing J2 variables {{{}}}".format( colour_items( variables ) ) )

    def __call__( self, target, source, env ):
        import os.path
        from jinja2 import Environment, FileSystemLoader

        path_offset = os.path.relpath( os.path.split( source[0].abspath )[0], start=self._base_path )
        logger.debug( "path_offset for rendered template files calculated as [{}]".format( as_notice( path_offset ) ) )
        templates_path = os.path.split( source[0].abspath )[0]
        logger.debug( "creating jinja2 environment using templates_path [{}]".format( as_notice( templates_path ) ) )
        self._jinja_env = Environment( loader=FileSystemLoader( templates_path ) )

        for s, t in zip( source, target ):
            source_file = os.path.split( s.abspath )[1]
            logger.debug( "reading and rendering template file [{}] to [{}]...".format( as_notice( source_file ), as_notice( t.path ) ) )
            template = self._jinja_env.get_template( source_file )
            logger.debug( "using variables {{{}}}".format( colour_items( self._variables ) ) )
            rendered_string = template.render( **self._variables )
            with open( t.abspath, "w" ) as output:
                output.write( rendered_string )

        return None


class RenderTemplateEmitter(object):

    def __init__( self, base_path, using_variables_file ):
        self._base_path = base_path
        self._using_variables_file = using_variables_file


    _jinja_extensions = set([
        ".j2",
        ".jinja2",
        ".jinja"
    ])


    @classmethod
    def _target_from( cls, path ):
        import os.path
        inner_path, outer_extension = os.path.splitext( path )
        file_path, inner_extension = os.path.splitext( inner_path )
        if outer_extension in cls._jinja_extensions:
            return inner_path
        elif inner_extension in cls._jinja_extensions:
            return file_path + outer_extension
        return path


    def __call__( self, target, source, env ):
        import os.path
        path_offset = os.path.relpath( os.path.split( source[0].abspath )[0], start=self._base_path )

        num_targets = len(target)
        for index, s in enumerate( self._using_variables_file and source[:-1] or source ):
            if index >= num_targets:
                source_file = os.path.split( s.abspath )[1]
                target_file = self._target_from( source_file )
                t = os.path.join( env['abs_final_dir'], path_offset, target_file )
                target.append( t )

        return target, source


class RenderJinjaTemplateMethod(object):

    def __call__( self, env, target, source, final_dir=None, base_path=None, variables=None, variables_file=None ):
        if final_dir == None:
            final_dir = env['abs_final_dir']

        if base_path == None:
            base_path = env['sconstruct_dir']

        if variables_file:
            path = str(variables_file)
            if not variables:
                variables = {}
            with open( path, 'r' ) as variables_json:
                data = json.load( variables_json )
                logger.debug( "loaded variables [{}] from file [{}]".format( colour_items( data ), as_notice( path ) ) )
                variables.update( data )

        using_variables_file = variables_file and True or False

        env.AppendUnique( BUILDERS = {
            'RenderJinjaTemplateBuilder' : env.Builder(
                action = RenderTemplateAction( base_path, variables ),
                emitter = RenderTemplateEmitter( base_path, using_variables_file )
        ) } )

        from SCons.Script import Flatten
        target = Flatten( target )
        source = Flatten( source )
        if using_variables_file:
            source.append( variables_file )

        rendered_templates = env.RenderJinjaTemplateBuilder( target, source )
        cuppa.progress.NotifyProgress.add( env, rendered_templates )
        return rendered_templates

    @classmethod
    def add_to_env( cls, cuppa_env ):
        cuppa_env.add_method( "RenderJinjaTemplate", cls() )