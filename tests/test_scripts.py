
"""
Unit tests for the various commissioning scripts.
"""

import unittest
import glob
import sys
import os
import json

currentDir = os.path.abspath(os.getcwd())
if os.path.exists(os.path.join(currentDir, 'test_scripts.py')):
    MODULE_BUILD = currentDir
else:
    MODULE_BUILD = None
    
run_scripts_tests = False
try:
    from io import StringIO
    from pylint.lint import Run
    from pylint.reporters.json_reporter import JSONReporter
    if MODULE_BUILD is not None:
        run_scripts_tests = True
        
        # Pre-seed TBF/Calibration/analysis.py
        os.system("%s ../TBF/Calibration/analysis.py" % sys.executable)
        
        # Pre-seed TBN/data.py
        os.system("%s ../TBN/data.py" % sys.executable)
        
except ImportError:
    pass


__version__  = "0.2"
__author__   = "Jayce Dowell"


_PYLINT_IGNORES = [('no-member',              "Module 'wx' has no"),
                   ('no-member',              "Module 'wx.html' has no"),
                   ('no-member',              "Module 'ephem' has no"),
                   ('no-member',              "Instance of 'Group' has no"),
                   ('no-member',              "Module 'datetime' has no 'fromtimestamp' member"),
                   ('no-member',              "Module 'matplotlib.cm' has no"),
                   ('no-name-in-module',      "No name 'c' in module 'astropy.constants'"),
                   ('bad-string-format-type', "Argument '.ndarray' does not match format")]


@unittest.skipUnless(run_scripts_tests, "requires the 'pylint' module")
class scripts_tests(unittest.TestCase):
    """A unittest.TestCase collection of unit tests for the commissioning scripts."""
    
    @staticmethod
    def _name_to_name(filename):
        filename = os.path.splitext(filename)[0]
        parts = filename.split(os.path.sep)
        start = parts.index('..')
        parts = parts[start+1:]
        return '_'.join(parts)
        
    def test_scripts(self):
        """Static analysis of the commissioning scripts."""
        
        _SCRIPTS = glob.glob(os.path.join(MODULE_BUILD, '..', '*.py'))
        for depth in range(1, 3):
            path = [MODULE_BUILD, '..']
            path.extend(['*',]*depth)
            path.append('*.py')
            _SCRIPTS.extend(glob.glob(os.path.join(*path)))
        _SCRIPTS = list(filter(lambda x: x.find('test_scripts.py') == -1, _SCRIPTS))
        _SCRIPTS = list(filter(lambda x: x.find('setup.py') == -1, _SCRIPTS))
        _SCRIPTS.sort()
        for script in _SCRIPTS:
            name = self._name_to_name(script)
            with self.subTest(script=name):
                pylint_output = StringIO()
                reporter = JSONReporter(pylint_output)
                Run([script, '-E', '--extension-pkg-allow-list=scipy.special,lsl.correlator._core'], reporter=reporter, exit=False)
                results = json.loads(pylint_output.getvalue())
                
                for i,entry in enumerate(results):
                    with self.subTest(error_number=i+1):
                        false_positive = False
                        for isym,imesg in _PYLINT_IGNORES:
                            if entry['symbol'] == isym and entry['message'].startswith(imesg):
                                false_positive = True
                                break
                        if false_positive:
                            continue
                            
                        self.assertTrue(False, f"{entry['path']}:{entry['line']} - {entry['symbol']} - {entry['message']}")


class scripts_test_suite(unittest.TestSuite):
    """A unittest.TestSuite class which contains all of the commissioning script
    tests."""
    
    def __init__(self):
        unittest.TestSuite.__init__(self)
        
        loader = unittest.TestLoader()
        self.addTests(loader.loadTestsFromTestCase(scripts_tests))


if __name__ == '__main__':
    unittest.main()
