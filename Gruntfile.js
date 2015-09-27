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
  });

  grunt.loadNpmTasks('grunt-shell');

  // set default tasks to run when grunt is called without parameters
  grunt.registerTask('default', ['runPythonTests']);

  grunt.registerTask('runPythonTests', ['shell:runPythonTests']);
};
