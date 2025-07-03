from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_predeterminada')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Integrante(db.Model):
    __tablename__ = 'integrantes'
    numero_documento = db.Column(db.String, primary_key=True)
    nombres = db.Column(db.String)
    apellidos = db.Column(db.String)
    fecha_nacimiento = db.Column(db.Date)
    sexo = db.Column(db.String)
    direccion = db.Column(db.String)
    telefono = db.Column(db.String)
    comunidad_indigena = db.Column(db.String)
    familia = db.Column(db.Integer)

@app.route('/')
def index():    
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']
        if usuario == 'admin' and clave == '1234':
            session['usuario'] = usuario
            return redirect(url_for('ver_integrantes'))
        else:
            flash('Usuario o contraseña incorrecta', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))


@app.route('integrantes')
def ver_integrantes():
    if 'usuario' not in session:
    return redirect(url_for('login'))
    consulta = request.args.get('buscar')
    orden = request.args.get('orden', 'familia') 
    columnas_validas = {
        'documento': Integrante.numero_documento,
        'nombres': Integrante.nombres,
        'apellidos': Integrante.apellidos,
        'fecha': Integrante.fecha_nacimiento,
        'sexo': Integrante.sexo,
        'comunidad': Integrante.comunidad_indigena,
        'familia': Integrante.familia,
    }

    columna_orden = columnas_validas.get(orden, Integrante.familia)
    
    if consulta:
        integrantes = Integrante.query.filter(
            Integrante.nombres.ilike(f'%{consulta}%') |
            Integrante.apellidos.ilike(f'%{consulta}%') |
            Integrante.comunidad_indigena.ilike(f'%{consulta}%') |
            Integrante.numero_documento.ilike(f'%{consulta}%')
        ).all()
    else:
        integrantes = Integrante.query.order_by(Integrante.familia).limit(100).all()

    return render_template('cabildo.html', integrantes=integrantes)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        try:
            nuevo = Integrante(
                numero_documento=request.form['documento'],
                nombres=request.form['nombres'].upper(),
                apellidos=request.form['apellidos'].upper(),
                fecha_nacimiento=datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d'),
                sexo=request.form['sexo'],
                direccion=request.form['direccion'],
                telefono=request.form['telefono'],
                comunidad_indigena=request.form['comunidad'],
                familia=int(request.form['familia'])
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Integrante agregado correctamente', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error al guardar: {e}', 'danger')
            return redirect(url_for('agregar'))
    return render_template('agregar.html')

@app.route('/eliminar/<documento>', methods=['POST'])
def eliminar(documento):
    integrante = Integrante.query.get(documento)
    if integrante:
        db.session.delete(integrante)
        db.session.commit()
        flash('Integrante eliminado', 'info')
    else:
        flash('No se encontró el integrante', 'warning')
    return redirect(url_for('cabildo'))

@app.route('/editar/<documento>', methods=['GET', 'POST'])
def editar(documento):
    integrante = Integrante.query.get_or_404(documento)
    if request.method == 'POST':
        try:
            integrante.nombres = request.form['nombres']
            integrante.apellidos = request.form['apellidos']
            integrante.fecha_nacimiento = datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d')
            integrante.sexo = request.form['sexo']
            integrante.direccion = request.form['direccion']
            integrante.telefono = request.form['telefono']
            integrante.comunidad_indigena = request.form['comunidad']
            integrante.familia = int(request.form['familia'])
            db.session.commit()
            flash('Datos actualizados correctamente', 'success')
            return redirect(url_for('cabildo'))
        except Exception as e:
            flash(f'Error al actualizar: {e}', 'danger')
            return redirect(url_for('editar', documento=documento))
    return render_template('editar.html', integrante=integrante)

@app.route('/importar', methods=['GET', 'POST'])
def importar():
    if request.method == 'POST':
        archivo = request.files['archivo']
        accion = request.form['accion']
        tabla_nombre = request.form['tabla_nombre']

        if not archivo.filename.endswith('.csv'):
            flash('Archivo inválido. Sube un archivo con extensión .csv', 'danger')
            return redirect(request.url)

        try:
            contenido = archivo.read().decode('utf-8')
            lector = csv.DictReader(io.StringIO(contenido), delimiter=';')
            columnas = lector.fieldnames

            if not columnas:
                flash('El archivo CSV no tiene encabezados.', 'danger')
                return redirect(request.url)

            if accion == 'nueva':
                columnas_sql = ', '.join([f'"{col}" TEXT' for col in columnas])
                crear_sql = f'CREATE TABLE IF NOT EXISTS "{tabla_nombre}" ({columnas_sql});'
                db.engine.execute(crear_sql)

            for fila in lector:
                columnas_insert = ', '.join([f'"{k}"' for k in fila])
                valores = "', '".join([fila[k].replace("'", "''") for k in fila])
                insertar_sql = f"INSERT INTO \"{tabla_nombre}\" ({columnas_insert}) VALUES ('{valores}');"
                db.engine.execute(insertar_sql)

            flash('Importación completada exitosamente.', 'success')
            return redirect('/')

        except Exception as e:
            flash(f'Error durante la importación: {e}', 'danger')
            return redirect(request.url)

    return render_template('importar.html')

if __name__ == '__main__':
    app.run(debug=True)
