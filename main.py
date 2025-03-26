# Import required libraries
from flask import Flask, render_template, request, redirect, url_for, jsonify  # Flask web framework for creating web applications
from peewee import SqliteDatabase, Model, IntegerField, TextField  # Database ORM for SQLite
import pandas as pd  # Data manipulation and analysis library
import matplotlib.pyplot as plt  # Plotting library for creating static visualizations
import seaborn as sns  # Statistical visualization library
import os  # Operating system interface
from datetime import datetime  # Date and time handling

# Initialize Flask application
app = Flask(__name__)

# Database configuration - using SQLite as the database
db = SqliteDatabase('data.db')


# Define the Data model for storing name and age information
class Data(Model):
    id = IntegerField(primary_key=True)  # Unique identifier for each record
    name = TextField()  # Field to store names
    age = IntegerField()  # Field to store ages

    class Meta:
        database = db  # Specify which database to use


# Function to initialize the database
def init_db():
    # Close any existing connections to prevent conflicts
    if not db.is_closed():
        db.close()
    
    # Delete existing database file if it exists to start fresh
    if os.path.exists('data.db'):
        os.remove('data.db')
    
    # Create new database connection
    db.connect()
    
    # Create tables based on the Data model
    db.create_tables([Data], safe=True)
    db.close()


# Initialize database when the application starts
init_db()


# Route for the main page - displays all data in a table
@app.route('/')
def index():
    try:
        # Ensure database connection is open
        if db.is_closed():
            db.connect()
        
        # Retrieve all records from the database
        data = list(Data.select().dicts())
        
        # Close database connection
        if not db.is_closed():
            db.close()
            
        return render_template('index.html', data=data)
    except Exception as e:
        print(f"Error in index: {str(e)}")
        return render_template('index.html', data=[])


# Route for handling file uploads - accepts CSV files with name and age data
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename.endswith('.csv'):
            try:
                # Read the CSV file with semicolon separator
                df = pd.read_csv(file, sep=';')
                print("Available columns:", df.columns.tolist())
                
                # Automatically detect name and age columns
                name_col = None
                age_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if 'name' in col_lower or 'label' in col_lower:
                        name_col = col
                    elif 'age' in col_lower:
                        age_col = col
                
                # Validate that required columns were found
                if name_col is None or age_col is None:
                    return "Error: Could not find appropriate columns. Please make sure your CSV has columns for names and ages."
                
                # Clean and process the age data
                df[age_col] = pd.to_numeric(df[age_col].astype(str).str.replace(r'[^\d.-]', ''), errors='coerce')
                df = df.dropna(subset=[age_col])
                
                # Insert data into the database
                for _, row in df.iterrows():
                    Data.create(
                        name=str(row[name_col]),
                        age=int(row[age_col])
                    )
                return redirect(url_for('index'))
            except Exception as e:
                return f"Error processing file: {str(e)}"
    return render_template('upload.html')


# Route for data visualization - creates various charts and graphs
@app.route('/visualize')
def visualize():
    try:
        # Get data from database and convert to pandas DataFrame
        data = pd.DataFrame(list(Data.select().dicts()))
        
        # Handle case when no data is available
        if data.empty:
            return render_template('visualize.html',
                                 error_message="Nav augšupielādētu datu. Lūdzu, vispirms augšupielādējiet CSV failu.",
                                 bar_plot=None,
                                 pie_plot=None,
                                 line_plot=None)
        
        # Create static directory for storing generated images
        if not os.path.exists('static'):
            os.makedirs('static')
        
        # 1. Create Bar Plot showing age distribution by name
        plt.figure(figsize=(10, 6))
        sns.barplot(data=data, x='name', y='age')
        plt.xticks(rotation=45)
        plt.title('Age Distribution by Name')
        plt.tight_layout()
        plt.savefig('static/barplot.png')
        plt.close()
        
        # 2. Create Pie Chart showing age group distribution
        plt.figure(figsize=(10, 6))
        # Group ages into categories
        age_groups = pd.cut(data['age'], bins=[0, 18, 30, 45, 60, 100], labels=['0-18', '19-30', '31-45', '46-60', '60+'])
        age_distribution = age_groups.value_counts()
        plt.pie(age_distribution, labels=age_distribution.index, autopct='%1.1f%%')
        plt.title('Age Distribution')
        plt.savefig('static/pieplot.png')
        plt.close()
        
        # 3. Create Box Plot showing age distribution statistics
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=data, y='age')
        plt.title('Age Distribution Box Plot')
        plt.savefig('static/lineplot.png')
        plt.close()
        
        return render_template('visualize.html',
                             error_message=None,
                             bar_plot='static/barplot.png',
                             pie_plot='static/pieplot.png',
                             line_plot='static/lineplot.png')
    except Exception as e:
        print(f"Error in visualize: {str(e)}")
        return render_template('visualize.html',
                             error_message="Radusies kļūda, mēģiniet vēlreiz",
                             bar_plot=None,
                             pie_plot=None,
                             line_plot=None)


# Route for filtering data based on age range
@app.route('/filter', methods=['GET', 'POST'])
def filter_data():
    filtered_data = []
    if request.method == 'POST':
        # Get age range from form
        min_age = int(request.form.get('min_value', 0))
        max_age = int(request.form.get('max_value', 100))
        
        # Query database for records within the age range
        query = Data.select().where(Data.age.between(min_age, max_age))
        filtered_data = list(query.dicts())
    
    return render_template('filter.html', data=filtered_data)


# API endpoint for getting statistical information about the data
@app.route('/api/stats')
def get_stats():
    try:
        # Ensure database connection
        if db.is_closed():
            db.connect()
        
        # Get all data
        data = list(Data.select().dicts())
        
        # Handle case when no data is available
        if not data:
            return jsonify({
                'total_records': 0,
                'average_age': 0,
                'max_age': 0,
                'min_age': 0
            })
        
        # Calculate statistics
        df = pd.DataFrame(data)
        stats = {
            'total_records': len(df),
            'average_age': float(df['age'].mean()),
            'max_age': int(df['age'].max()),
            'min_age': int(df['age'].min())
        }
        
        # Close database connection
        if not db.is_closed():
            db.close()
            
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_stats: {str(e)}")
        return jsonify({
            'total_records': 0,
            'average_age': 0,
            'max_age': 0,
            'min_age': 0
        })


# API endpoint for clearing all data from the database
@app.route('/clear_data', methods=['POST'])
def clear_data():
    try:
        # Ensure database connection
        if db.is_closed():
            db.connect()
        
        # Delete all records in a transaction
        with db.atomic():
            Data.delete().execute()
        
        # Close database connection
        if not db.is_closed():
            db.close()
            
        return jsonify({'success': True, 'message': 'All data has been cleared'})
    except Exception as e:
        print(f"Error clearing data: {str(e)}")
        if not db.is_closed():
            db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# Start the Flask application in debug mode
if __name__ == '__main__':
    app.run(debug=True)