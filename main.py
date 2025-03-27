# Nepieciešamo bibliotēku importēšana
from flask import Flask, render_template, request, redirect, url_for, jsonify  # Flask tīmekļa ietvara bibliotēka
from peewee import SqliteDatabase, Model, IntegerField, TextField  # Datubāzes ORM bibliotēka SQLite
import pandas as pd  # Datu manipulācijas un analīzes bibliotēka
import matplotlib.pyplot as plt  # Grafiku veidošanas bibliotēka
import seaborn as sns  # Statistiskās vizualizācijas bibliotēka
import os  # Operētājsistēmas saskarnes bibliotēka
from datetime import datetime  # Datuma un laika apstrādes bibliotēka

# Flask aplikācijas inicializēšana
app = Flask(__name__)

# Datubāzes konfigurācija - izmantojam SQLite
db = SqliteDatabase('data.db')


# Datu modeļa definēšana vārdu un vecumu informācijas glabāšanai
class Data(Model):
    id = IntegerField(primary_key=True)  # Unikāls identifikators katram ierakstam
    name = TextField()  # Lauks vārdu glabāšanai
    age = IntegerField()  # Lauks vecumu glabāšanai

    class Meta:
        database = db  # Norāda, kuru datubāzi izmantot


# Funkcija datubāzes inicializēšanai
def init_db():
    if not db.is_closed():
        db.close()
    
    if os.path.exists('data.db'):
        os.remove('data.db')
    
    # Izveidot jaunu datubāzes savienojumu
    db.connect()
    
    # Izveidot tabulas pēc datu modeļa
    db.create_tables([Data], safe=True)
    db.close()


# Inicializēt datubāzi, kad aplikācija sāk darboties
init_db()


# Galvenās lapas maršruts - parāda visus datus tabulā
@app.route('/')
def index():
    try:
        if db.is_closed():
            db.connect()
        
        # Iegūst visus ierakstus no datubāzes
        data = list(Data.select().dicts())
        
        if not db.is_closed():
            db.close()
            
        return render_template('index.html', data=data)
    except Exception as e:
        print(f"Kļūda index lapā: {str(e)}")
        return render_template('index.html', data=[])


# Failu augšupielādes maršruts - pieņem CSV failus ar vārdu un vecumu datiem
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename.endswith('.csv'):
            try:
                # Lasīt CSV failu ar semikola vai komata atdalītāju
                try:
                    df = pd.read_csv(file, sep=';')
                except:
                    df = pd.read_csv(file, sep=',')
                print("Pieejamās kolonnas:", df.columns.tolist())
                
                # Atrast vārdu un vecuma kolonnas
                name_col = None
                age_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if 'name' in col_lower or 'label' in col_lower:
                        name_col = col
                    elif 'age' in col_lower:
                        age_col = col
                
                # Pārbaudīt, vai atrastas nepieciešamās kolonnas
                if name_col is None or age_col is None:
                    return "Kļūda: Nevarēja atrast atbilstošas kolonnas. Lūdzu, pārliecinieties, ka CSV failā ir kolonnas vārdiem un vecumiem."
                
                # Apstrādāt vecuma datus
                df[age_col] = pd.to_numeric(df[age_col].astype(str).str.replace(r'[^\d.-]', ''), errors='coerce')
                df = df.dropna(subset=[age_col])
                
                # Ievietot datus datubāzē
                for _, row in df.iterrows():
                    Data.create(
                        name=str(row[name_col]),
                        age=int(row[age_col])
                    )
                return redirect(url_for('index'))
            except Exception as e:
                return f"Kļūda faila apstrādē: {str(e)}"
    return render_template('upload.html')


# Datu vizualizācijas maršruts - izveido dažādus grafikus un diagrammas
@app.route('/visualize')
def visualize():
    try:
        # Iegūstam datus no datubāzes un pārvēršam tos pandas DataFrame
        data = pd.DataFrame(list(Data.select().dicts()))
        
        if data.empty:
            return render_template('visualize.html',
                                 error_message="Nav augšupielādētu datu. Lūdzu, vispirms augšupielādējiet CSV failu.",
                                 bar_plot=None,
                                 pie_plot=None,
                                 line_plot=None)
        
        # Izveidot static direktoriju attēlu glabāšanai
        if not os.path.exists('static'):
            os.makedirs('static')
        
        # Izveidot Stabveida Diagrammu, kas parāda vecuma sadalījumu pēc vārdiem
        plt.figure(figsize=(10, 6))
        sns.barplot(data=data, x='name', y='age')
        plt.xticks(rotation=45)
        plt.title('Vecuma sadalījums pēc vārdiem')
        plt.tight_layout()
        plt.savefig('static/barplot.png')
        plt.close()
        
        # Izveidot Pīrāga Diagrammu, kas parāda vecuma grupu sadalījumu
        plt.figure(figsize=(10, 6))
        # Grupējam vecumus kategorijās
        age_groups = pd.cut(data['age'], bins=[0, 18, 30, 45, 60, 100], labels=['0-18', '19-30', '31-45', '46-60', '60+'])
        age_distribution = age_groups.value_counts()
        plt.pie(age_distribution, labels=age_distribution.index, autopct='%1.1f%%')
        plt.title('Vecuma sadalījums')
        plt.savefig('static/pieplot.png')
        plt.close()
        
        # Izveidot Kastes Diagrammu, kas parāda vecuma sadalījuma statistiku
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=data, y='age')
        plt.title('Vecuma sadalījuma kastes diagramma')
        plt.savefig('static/lineplot.png')
        plt.close()
        
        return render_template('visualize.html',
                             error_message=None,
                             bar_plot='static/barplot.png',
                             pie_plot='static/pieplot.png',
                             line_plot='static/lineplot.png')
    except Exception as e:
        print(f"Kļūda visualize lapā: {str(e)}")
        return render_template('visualize.html',
                             error_message="Radusies kļūda, mēģiniet vēlreiz",
                             bar_plot=None,
                             pie_plot=None,
                             line_plot=None)


# Datu filtrēšanas maršruts pēc vecuma diapazona
@app.route('/filter', methods=['GET', 'POST'])
def filter_data():
    filtered_data = []
    if request.method == 'POST':
        # Iegūt vecuma diapazonu no formas
        min_age = int(request.form.get('min_value', 0))
        max_age = int(request.form.get('max_value', 100))
        
        # Sameklēt ierakstus datubāzē pēc vecuma diapazona
        query = Data.select().where(Data.age.between(min_age, max_age))
        filtered_data = list(query.dicts())
    
    return render_template('filter.html', data=filtered_data)


# API galapunkts statistiskās informācijas iegūšanai par datiem
@app.route('/api/stats')
def get_stats():
    try:
        if db.is_closed():
            db.connect()
        
        # Iegūt visus datus
        data = list(Data.select().dicts())
        
        if not data:
            return jsonify({
                'total_records': 0,
                'average_age': 0,
                'max_age': 0,
                'min_age': 0
            })
        
        # Aprēķināt statistiku
        df = pd.DataFrame(data)
        stats = {
            'total_records': len(df),
            'average_age': float(df['age'].mean()),
            'max_age': int(df['age'].max()),
            'min_age': int(df['age'].min())
        }
        
        if not db.is_closed():
            db.close()
            
        return jsonify(stats)
    except Exception as e:
        print(f"Kļūda get_stats: {str(e)}")
        return jsonify({
            'total_records': 0,
            'average_age': 0,
            'max_age': 0,
            'min_age': 0
        })


# API galapunkts visu datu izdzēšanai no datubāzes
@app.route('/clear_data', methods=['POST'])
def clear_data():
    try:
        if db.is_closed():
            db.connect()
        
        with db.atomic():
            Data.delete().execute()
        
        if not db.is_closed():
            db.close()
            
        return jsonify({'success': True, 'message': 'Visi dati ir izdzēsti'})
    except Exception as e:
        print(f"Kļūda datu izdzēšanā: {str(e)}")
        if not db.is_closed():
            db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# Flask servera palaišana debug režīmā
if __name__ == '__main__':
    app.run(debug=True)