from flask import Flask, request, jsonify, g
import sqlite3
import os

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Create the database directory if it doesn't exist
if not os.path.exists('db'):
    os.makedirs('db')

# Path to the database file
DATABASE_PATH = os.path.join('db', 'history.db')


history = []  # Initialize a list to store the calculation history
def init_db():
    db = sqlite3.connect(DATABASE_PATH)
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()

# Function to perform arithmetic calculations given an expression
def calculate_expression(expression):
    # Dictionary of operator functions for calculations
    operators = {
        'plus': lambda x, y: x + y,
        'minus': lambda x, y: x - y,
        'multiply': lambda x, y: x * y,
        'divide': lambda x, y: x / y
    }

    # Precedence of operators for handling order of operations
    precedence = {
        'multiply': 2,
        'divide': 2,
        'plus': 1,
        'minus': 1
    }

    tokens = expression.split('/')  # Split the expression into tokens
    operators_stack = []  # Stack to hold operators
    operands_stack = []   # Stack to hold operands

    for token in tokens:
        if token in operators:  # If the token is an operator
            # Perform calculations respecting precedence
            while (operators_stack and
                   precedence[operators_stack[-1]] >= precedence[token]):
                operator = operators_stack.pop()
                operand2 = operands_stack.pop()
                operand1 = operands_stack.pop()
                result = operators[operator](operand1, operand2)
                operands_stack.append(result)
            operators_stack.append(token)
        else:  # If the token is an operand
            operands_stack.append(float(token))

    # Perform remaining calculations
    while operators_stack:
        operator = operators_stack.pop()
        operand2 = operands_stack.pop()
        operand1 = operands_stack.pop()
        result = operators[operator](operand1, operand2)
        operands_stack.append(result)

    return operands_stack[0]  # The final result of the expression

# Function to convert user-friendly expression to a valid expression
def convert_expression(input_string):
    operators = {'plus': '+', 'minus': '-', 'multiply': '*', 'divide': '/'}
    tokens = input_string.split('/')  # Split the input string into tokens
    expression = tokens[0]  # Initialize the expression with the first token
    
    # Iterate over operator and operand pairs
    for i in range(1, len(tokens), 2):
        operator = operators.get(tokens[i])  # Get the corresponding operator
        operand = tokens[i+1]  # Get the operand
        expression += f"{operator}{operand}"  # Add operator and operand to expression
        
    return expression  # Return the converted expression

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_PATH)
    return db

@app.teardown_appcontext
def close_db_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Route to get the calculation history
@app.route('/history', methods=['GET'])
def get_history():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT question, answer FROM history ORDER BY id DESC LIMIT 20')
    rows = cursor.fetchall()
    history_data = [{'question': row[0], 'answer': row[1]} for row in rows]
    return jsonify(history_data)# Return the history as JSON response

# Route to perform arithmetic operations and store in history
@app.route('/<path:operations>', methods=['GET'])
def perform_operations(operations):
    question = convert_expression(operations)
    answer = int(calculate_expression(operations))
    operation = {'question': question, 'answer': answer}

    db = get_db()
    cursor = db.cursor()

    cursor.execute('INSERT INTO history (question, answer) VALUES (?, ?)', (question, answer))
    db.commit()

    cursor.execute('SELECT COUNT(*) FROM history')
    count = cursor.fetchone()[0]
    if count > 20:
        cursor.execute('DELETE FROM history WHERE id = (SELECT MIN(id) FROM history)')
        db.commit()

    return jsonify(operation) # Return operation details

if __name__ == '__main__':
    if not os.path.exists(DATABASE_PATH):
        init_db()
    app.run(host='localhost', port=3000)  # Start the Flask app on localhost:3000
