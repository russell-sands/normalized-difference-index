import arcpy


class Toolbox(object):
    def __init__(self):
        '''Define the toolbox (the name of the toolbox is the name of the
        .pyt file).'''
        self.label = 'Toolbox'
        self.alias = ''

        # List of tool classes associated with this toolbox
        self.tools = [Calculate]


class Calculate(object):
    def __init__(self):
        '''Define the tool (tool name is the name of the class).'''
        self.label = 'Calculate Normalized Difference Index'
        self.description = ''
        self.canRunInBackground = False

    def getParameterInfo(self):
        '''Define parameter definitions'''
        p0 = arcpy.Parameter(
          displayName = 'Input Features',
          name = 'in_features',
          datatype = 'GPFeatureLayer',
          parameterType = 'Required',
          direction = 'Input'
        ) 

        p1 = arcpy.Parameter(
          displayName = 'Field that should cause the index to approach 1',
          name = 'fieldPositiveOne',
          datatype = 'Field',
          parameterType = 'Required',
          direction = 'Input'
        )
        p1.parameterDependencies = [p0.name]
        p1.filter.list = ['Short', 'Long', 'Double']

        p2 = arcpy.Parameter(
          displayName = 'Field that should casue the index to approach -1',
          name = 'fieldNegativeOne',
          datatype = 'Field',
          parameterType = 'Required',
          direction = 'Input'
          )
        p2.parameterDependencies = [p0.name]
        p2.filter.list = p1.filter.list

        p3 = arcpy.Parameter(
          displayName = 'Is there an ideal relationship?',
          name = 'idealValue',
          datatype = 'String',
          parameterType = 'Required',
          direction = 'Input',
          enabled = False # Only shows when 1 & 2 are defined, see logic
          )
        p3.filter.type = 'ValueList'
        p3.filter.list = ['Yes', 'No']

        p4 = arcpy.Parameter(
          displayName = 'How is the relationship defined?',
          name = 'relationshipDirection',
          datatype = 'String',
          parameterType = 'Optional',
          direction = 'Input',
          enabled = False
          )
        p4.filter.type = 'ValueList'

        p5 = arcpy.Parameter(
          displayName = 'What is the relationship (eg. 2:1)?',
          name = 'relationshipValue',
          datatype = 'String',
          parameterType = 'Optional',
          direction = 'Input',
          enabled = False
          )

        p6 = arcpy.Parameter(
          displayName = 'Output Field',
          name = 'fieldOutput',
          datatype = 'Field',
          parameterType = 'Required',
          direction = 'Ouptut'
          )

        params = [p0, p1, p2, p3, p4, p5, p6] 
        return params

    def isLicensed(self):
        '''Set whether tool is licensed to execute.'''
        return True

    def updateParameters(self, parameters):
        '''Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed.'''

        # Only show the weight toggle if the value fields are both defined and not the same.
        if parameters[1].value and parameters[2].value and not parameters[1].valueAsText == parameters[2].valueAsText:
            parameters[3].enabled = True
        else:
            parameters[3].value = None
            parameters[3].enabled = False

        # Display and control the behavior of weighting settings based on user
        # input
        if parameters[3].value == 'Yes':
            parameters[4].enabled = True
            parameters[4].filter.list = [
              ' : '.join([parameters[1].valueAsText, parameters[2].valueAsText]),
              ' : '.join([parameters[2].valueAsText, parameters[1].valueAsText]),
              ]
            if parameters[4].value:
                parameters[5].enabled = True
            else:
                parameters[5].enabled = False
        else:
            parameters[4].enabled = False
            parameters[5].enabled = False
            parameters[4].value = None
            parameters[5].value = None        
        return

    def updateMessages(self, parameters):
        '''Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation.'''

        # Don't allow the two input fields to be the same field
        if parameters[1].valueAsText == parameters[2].valueAsText:
            msg = "Input fields must not be the same"
            parameters[1].setErrorMessage(msg)
            parameters[2].setErrorMessage(msg)

        # Don't let the user submit if they indicated a relationship is 
        # desired but didn't specify one
        if parameters[3].value == 'Yes':
            if not parameters[4].value:
                parameters[4].setErrorMessage('Relationship direction must be defined')
            elif not parameters[5].value:
                # Bit of a proxy for an AND. Else will trigger IF p4 is defined, and we'll only
                # get here if p4 has a value AND p5 does not have a value. 
                parameters[5].setErrorMessage('Relationship value must be defined')


        # Validate the format of the relationship
        if parameters[5].value:
            if ':' not in parameters[5].value:
                parameters[5].setErrorMessage('Incorrect format. No colon found. Must be two numbers separated by a colon e.g. 2:1')
            else:
                a, b = parameters[5].value.split(':')
                try:
                    float(a)
                    float(b)
                except ValueError:
                    Sparameters[5].setErrorMessage('Incorrect format. Unable to parse numbers. Value must be two numbers separated by a colon eg. 2:1')

        return


    def execute(self, parameters, messages):
        '''The source code of the tool.'''
        
        # Read the input parameters
        inputFeatures = parameters[0].value
        fieldOnePos = parameters[1].valueAsText
        fieldOneNeg = parameters[2].valueAsText
        isIdeal = parameters[3].value
        relationshipDirection = parameters[4].valueAsText
        relationshipValue = parameters[5].valueAsText
        outputField = parameters[6].valueAsText

        # Build out a dictionary that will help with the math later
        relationshipWeights = {}
        if isIdeal == 'Yes':
            field1, field2 = [f.strip() for f in relationshipDirection.split(':')]
            weight1, weight2 = [float(w) for w in relationshipValue.split(':')]
            relationshipWeights[field1] = weight1
            relationshipWeights[field2] = weight2
        else:
            relationshipWeights[fieldOnePos] = 1
            relationshipWeights[fieldOneNeg] = 1
        arcpy.AddMessage(relationshipWeights)
        # Add the output field
        arcpy.AddField_management(inputFeatures, outputField, 'DOUBLE')

        # Perform the calculation in a cursor for simplicity
        with arcpy.da.UpdateCursor(inputFeatures, [fieldOnePos, fieldOneNeg, outputField]) as update:
            for row in update:
                valOnePos = row[0]
                valOneNeg = row[1]
                wOnePos = relationshipWeights[fieldOnePos]
                wOneNeg = relationshipWeights[fieldOneNeg]
                # Calculating this ahead of time so that I can check the denominator and avoid
                # a zero division
                top = (valOnePos / wOnePos) - (valOneNeg / wOneNeg)
                bottom = (valOnePos / wOnePos) + (valOneNeg / wOneNeg)
                if bottom == 0:
                    index = None
                else:
                    index = top / bottom
                update.updateRow([valOnePos, valOneNeg, index])
        return