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
      vulcanize: {
        command: 'vulcanize --inline-scripts --inline-css --strip-comments components.html > vulcanized.html'
      },
    },
  });

  grunt.loadNpmTasks('grunt-shell');

  // set default tasks to run when grunt is called without parameters
  grunt.registerTask('default', ['vulcanize'], ['runPythonTests']);

  grunt.registerTask('vulcanize', ['shell:vulcanize']);
  grunt.registerTask('runPythonTests', ['shell:runPythonTests']);
};
