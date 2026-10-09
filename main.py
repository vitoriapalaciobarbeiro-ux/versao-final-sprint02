from flask import Flask, render_template, request, flash, redirect, url_for, session
import fdb
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'Meu-salario'

#conectar o banco:
host = 'localhost'
database = r'C:\Users\rehme\OneDrive\Ambiente de Trabalho\projeto MS\BANCO.FDB'
user = 'sysdba'
password = 'sysdba'

con = fdb.connect(host=host, database=database, user=user, password=password,) #conectar o banco

@app.route('/')
def index():
    return render_template('index.html')

def validar_senha(senha):
    if len(senha) < 8:
      return False
    tem_maiusculo = False
    tem_minusculo = False
    tem_numero = False

    for caractere in senha:
      if caractere.isupper():
          tem_maiusculo = True

      if caractere.islower():
          tem_minusculo = True

      if caractere.isdigit():
          tem_numero = True

    if tem_maiusculo == False:
      return False

    if tem_minusculo == False:
      return False

    if tem_numero == False:
      return False

    if senha.strip() == "":
        return False

    return True

#CADASTRAR
@app.route('/cadastro')
def cadastro():
  return render_template('cadastro.html')

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
  nome = request.form['nome']
  email = request.form['email']
  senha = request.form['senha']
  confirmar = request.form['confirmar']

  if not validar_senha(senha):
       flash('Senha fraca!')
       return redirect(url_for('cadastro'))

  senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
  cursor = con.cursor()

  if senha != confirmar:
      flash('As senhas não são iguais!')
      return redirect(url_for('cadastro'))
  else:
      try:
           cursor.execute(""" SELECT 1
                              FROM usuario
                              WHERE email = ?""", (email,))
           if cursor.fetchone() is not None:
               flash("Erro: Usuário já cadastrado!")
               return redirect(url_for('cadastro'))

           cursor.execute("""INSERT INTO usuario (nome, email, senha, valor_diario_padrao, valor_diario_excepcional, valor_pacotes)
                                values (?, ?, ?, ?, ?, ?)""", (nome, email, senha_hash, 0, 0, 0))
           con.commit()

      except Exception as e:
           flash(f"Ocorreu um erro! -> {e}")
           con.rollback()

      finally:
           cursor.close()

      return redirect(url_for('login'))

#LOGIN
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/entrar', methods=['GET', 'POST'])
def entrar():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        cursor = con.cursor()
        try:
            cursor.execute("""SELECT ID_USUARIO, SENHA, TENTATIVA, STATUS, NOME FROM USUARIO WHERE EMAIL = ?""", (email,))
            usuario = cursor.fetchone()
            if not usuario: #seleciona um único valor
               flash('Usuário não encontrado!')
               return redirect(url_for('login'))

            id_usuario, senha_hash, tentativa, status, nome = usuario

            if status == 0:
                if usuario:
                    if bcrypt.check_password_hash(senha_hash, senha):
                        session['id_usuario'] = id_usuario
                        session['nome'] = nome

                        flash('Login bem-sucedido!')
                        tentativas = 0
                        cursor.execute('update usuario set tentativa = ? where id_usuario = ?',
                                       (tentativas, id_usuario))
                        con.commit()

                        return redirect(url_for('dashboard'))

                    else:
                        tentativa += 1
                        cursor.execute('update usuario set tentativa = ? where id_usuario = ?',(tentativa,id_usuario))
                        con.commit()

                        if tentativa == 3:
                            cursor.execute('update usuario set status = 1 where id_usuario = ?', (id_usuario,))
                            con.commit()
                            flash('Usuário está bloqueado , entre em contato com o administrador do sistema!')
                            return redirect(url_for('login'))

                        flash(f'Email ou senha inválidos!')
                        return redirect(url_for('login'))

                else:
                    return render_template('login.html')
            else:
                flash('Usuário Inativo!')
                return render_template('login.html')


        except Exception as e:
            flash(f'Ocorreu um erro -> {e}')
            con.rollback()

        finally:
            cursor.close()

        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('id_usuario', None)
    flash('Logout com sucesso!')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))
    else:
        return render_template('dashboard.html', nome=session['nome'])

def buscarUsuario(id):
    id = session['id_usuario']

    cursor = con.cursor()
    cursor.execute("""SELECT ID_USUARIO, NOME, email, senha, VALOR_DIARIO_PADRAO, VALOR_DIARIO_EXCEPCIONAL, VALOR_PACOTES
                             FROM USUARIO
                             WHERE id_usuario = ?""", (id,))
    usuario = cursor.fetchone()
    cursor.close()

    return usuario

@app.route('/editar_usuario')
def editar_usuario():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()

        cursor.execute("""SELECT ID_USUARIO, NOME, email, senha, VALOR_DIARIO_PADRAO, VALOR_DIARIO_EXCEPCIONAL, VALOR_PACOTES
                                FROM USUARIO
                                WHERE id_usuario = ?""", (session['id_usuario'],))
        usuario = cursor.fetchone()

        cursor.close()

        return render_template('editar_usuario.html', usuario=usuario, nome = usuario[1])

@app.route('/editar', methods=['GET', 'POST'])
def editar():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))
    else:
       cursor = con.cursor()

       try:
           id = session['id_usuario']

           usuario = buscarUsuario(session['id_usuario'])

           print(request.method)

           if request.method == 'POST':
               nome = request.form['nome']
               email = request.form['email']
               valor_padrao = float(request.form['valor_padrao'])
               valor_excepcional = float(request.form['valor_excepcional'])
               valor_pacotes = float(request.form['valor_pacotes'])

               if nome.strip() and email.strip() != "":

                   cursor.execute("""UPDATE USUARIO
                                       SET NOME = ?,
                                       EMAIL = ?,
                                       VALOR_DIARIO_PADRAO = ?,
                                       VALOR_DIARIO_EXCEPCIONAL = ?,
                                       VALOR_PACOTES = ?
                                       WHERE ID_USUARIO = ?""",
                                  (nome, email, valor_padrao, valor_excepcional, valor_pacotes, id))
                   con.commit()

                   flash("Usuário editado com sucesso!")

                   usuario = buscarUsuario(id)

               else:
                  flash('Não podem existir campos nulos!')
       except Exception as e:
            print(e)
            flash(f"Ocorreu um erro! -> {e}")

       finally:
            return render_template('editar_usuario.html', nome=usuario[1], usuario=usuario)


def senhas_anteriores(senha_modificada):
    cursor = con.cursor()
    id_usuario = session['id_usuario']

    cursor.execute("""SELECT SENHA, SENHA1, SENHA2 FROM USUARIO WHERE ID_USUARIO = ?""",(id_usuario,))
    senha_atual, senha1, senha2 = cursor.fetchone()

    if (bcrypt.check_password_hash(senha_atual, senha_modificada) or
            (senha1 and bcrypt.check_password_hash(senha1, senha_modificada)) or
            (senha2 and bcrypt.check_password_hash(senha2, senha_modificada))):
        return False
    else:
        alt_senha2 = senha_atual
        alt_senha1 = senha2
        alt_senha = bcrypt.generate_password_hash(senha_modificada).decode('utf-8')

        print(alt_senha, alt_senha1, alt_senha2)

        cursor.execute("""UPDATE USUARIO SET SENHA = ?, SENHA1 = ?, SENHA2 = ? WHERE ID_USUARIO = ?""", (alt_senha, alt_senha1, alt_senha2, id_usuario))
        cursor.close()

        return True

@app.route('/editar_senha')
def editar_senha():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))
    else:
        nome = buscarUsuario(id)[1]
        return render_template('editar_senha.html', nome = nome)


@app.route('/senha', methods=['GET', 'POST'])
def senha():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))


    else:
        cursor = con.cursor()
        try:
            id = session['id_usuario']
            usuario = buscarUsuario(id)
            print("ID:", id)
            print("USUARIO:", usuario)
            print("TIPO:", type(usuario))

            if request.method == 'POST':
                senha_atual = request.form['senha_atual']
                nova_senha = request.form['nova_senha']
                confirma_senha = request.form['confirma_senha']

                if bcrypt.check_password_hash(usuario[3], senha_atual):
                    if nova_senha == confirma_senha:
                        if validar_senha(nova_senha):
                            if senhas_anteriores(nova_senha):
                                flash("Senha alterada com sucesso!")
                            else:
                                flash("A senha tem que ser diferente das anteriores!")
                        else:
                            flash("Informe uma senha segura!")
                    else:
                        flash("As senhas não são iguais!")
                else:
                    flash("Senha incorreta!")


        except Exception as e:
            print(e)
            flash(f"Ocorreu um erro! -> {e}")

        finally:
            cursor.close()

        nome = usuario[1]
        return render_template('editar_senha.html', usuario=usuario, nome=nome)

if __name__ == '__main__':
    app.run(debug=True)
