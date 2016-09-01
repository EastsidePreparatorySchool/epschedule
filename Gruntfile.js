'use strict';

module.exports = function(grunt) {
  // configure project
  grunt.initConfig({
    // make node configurations available
    pkg: grunt.file.readJSON('package.json'),

    shell: {
      runPythonTests: {
        command: 'python ./build/run_python_tests.py .'
      },
    },
    vulcanize: {
      default: {
        options: {
          inlineScripts: true,
          inlineCss: true,
          stripComments: true
        },
        files: {
          'vulcanized.html': 'components.html'
        }
      },
    }
  });

  grunt.loadNpmTasks('grunt-shell');
  grunt.loadNpmTasks('grunt-vulcanize');

  // set default tasks to run when grunt is called without parameters
  grunt.registerTask('default', ['vulcanize'], ['runPythonTests']);

  //grunt.registerTask('vulcanize', ['vulcanize']);
  grunt.registerTask('runPythonTests', ['shell:runPythonTests']);
};
