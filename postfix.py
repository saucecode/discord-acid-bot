#!/usr/bin/env python
# postfix.py - a postfix calculator for python 2 & 3
# version 7    2016-09-25

import string, sys
import cmath, math
import inspect
import readline

def countFunctionArguments(func):
	try:
		return len(inspect.signature(func).parameters)
	except:
		return len(inspect.getargspec(func).args)

def is_number(s):
	try:
		complex(s)
		return True
	except ValueError:
		return False

variables = {'pi':math.pi, '-pi':-math.pi, 'e':math.e, '-e':math.e, 'i':1.0j, '-i':-1.0j, '\\':1.0}
def variableAssign(a,b):
	variables[a] = variables[b] if b in variables else b
	if a[0] == '-':
		variables[a[1:]] = -1.0 * (variables[b] if b in variables else b)
	else:
		variables['-'+a] = -1.0 * (variables[b] if b in variables else b)
	return b

OPERATIONS = {
	'+' : lambda a,b:a+b,
	'-' : lambda a,b:b-a,
	'/' : lambda a,b:b/a,
	'*' : lambda a,b:a*b,
	'**' : lambda a,b:b**a,
	'sin' : lambda a:cmath.sin(a),
	'cos' : lambda a:cmath.cos(a),
	'tan' : lambda a:cmath.tan(a),
	'atan' : lambda a:cmath.atan(a),
	'asin' : lambda a:cmath.asin(a),
	'acos' : lambda a:cmath.acos(a),
	'sqrt' : lambda a:a**0.5,
	'%' : lambda a,b:b%a,
	'ln' : lambda a:cmath.log(a),
	'log' : lambda a,b:cmath.log(b,a),
	'rad' : lambda a:math.radians(a.real),
	'deg' : lambda a:math.degrees(a.real),
	
	'arg' : lambda a:cmath.phase(a),
	'abs' : lambda a:(a.real*a.real + a.imag*a.imag)**0.5,
	'Re' : lambda a:a.real,
	'Im' : lambda a:a.imag,
	
	'=' : variableAssign
}

def executeOp(opid, args):
	if opid == '=':
		return OPERATIONS[opid](*[complex(i) if is_number(i) else i for i in args])
	else:
		return OPERATIONS[opid](*[complex(variables[i]) if i in variables else complex(i) for i in args])

def doPostfix(postfix_string):
	calc = postfix_string.split(' ')
	if calc[0] == '': return
	
	stack = []
	for i in calc:
		if is_number(i) or i in variables:
			stack.append(i)
		elif i in OPERATIONS:
			argCount = countFunctionArguments(OPERATIONS[i])
			args=[]
			for ii in range(argCount):
				args.append(stack.pop(-1))
			ans = executeOp(i, args)
			stack.append(ans)
		else:
			stack.append(i)
	if len(stack) == 1:
		variables['\\'] = complex([variables[elm] if elm in variables else elm for elm in stack][0])
	return [variables[elm] if elm in variables else elm for elm in stack]

def outputResult(result):
	return ', '.join([str(complex(item)) if complex(item).imag != 0 else str(complex(item).real) for item in result])
	

if __name__ == '__main__':
	print('saucecode\'s postfix v7    2016-09-25')

	try:
		raw_input
	except:
		raw_input = input

	while 1:
		try:
			output = doPostfix(raw_input('> '))
			print(outputResult(output))
		except TypeError as e:
			print('')
			continue
		except KeyboardInterrupt as e:
			print('Bye!')
			sys.exit(0)
		except ZeroDivisionError as e:
			print('Division by zero')
			continue
