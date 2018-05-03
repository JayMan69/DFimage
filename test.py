import sys

if len(sys.argv) == 1:
	print ('Default')
else:
	if len(sys.argv) == 2:
		variable = sys.argv[1].split('=')
		if variable[0] == '--resource':
			resource = variable[1]
			print('resource =',resource )

		if variable[0] == '--type':
			type = variable[1]
			print('type =',type)


	else:
		if len(sys.argv) == 3:
			print ('2 input variables')
			#print (sys.argv[2])

		variable = sys.argv[1].split('=')
		print (variable)
		if variable[0] == '--resource':
			resource = variable[1]
			print('resource =',resource )

			variable2 = sys.argv[2].split('=')
			type = variable[1]
			print('type =',type )

		else:
			if variable[0] == '--type':
				type = variable[1]
				print('type =',type)
				variable2 = sys.argv[2].split('=')
				resource = variable2[1]
				print('resource =',resource )
