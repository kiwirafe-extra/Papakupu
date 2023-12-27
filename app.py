from flask import *
import sqlite3
import os
import hashlib
import time

app = Flask(__name__)
PROJECT_ROOT = app.root_path
DATABASE = os.path.join(PROJECT_ROOT, 'dictionary.db')  # The database file for this project
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'static/images')  # Folder that the images of words is saved in
app.secret_key = "mHrli-#iuP{y):K"  # Hash key
TEACHER_CODE = "1234"  # Teacher Code that proves the user is actually a user


def get_db(query, args=(), fetch_type="all"):
    """
    This function connects to the database and fetch all the data that the user needs.
    :param query: the SQL query that the user wants to execute
    :param args: the SQL arguments that the query requires
    :param fetch_type: whether the user wants to fetch one row or all the rows
    :return: the list of all the rows fetched
    """
    connection = sqlite3.connect(DATABASE)
    cur = connection.cursor()
    cur.execute(query, args)
    if fetch_type == "one":
        data = cur.fetchone()
    else:
        data = cur.fetchall()
    connection.close()

    return data


def exec_db(query, args=()):
    """
    This function connects to the database and executes the query,
    for example the user can add or delete rows to the database.
    :param query: the SQL query that the user wants to execute
    :param args: the SQL arguments that the query requires
    """
    connection = sqlite3.connect(DATABASE)
    cur = connection.cursor()
    cur.execute(query, args)
    connection.commit()
    connection.close()


@app.route('/', methods=['GET', 'POST'])
def home():
    """
    This function serves the homepage and provides the search functionality.
    :return:
        For POST method, this function gets the value in the search box and
        find the associated word. If there's a word found, return
        the information about the word. If not, return -1 which will let HTML to
        display 'Not Found'.
        For GET method, this function returns a basic Home HTML file.
    """
    if request.method == "POST":
        query = request.form.get('searchbox').strip().lower()
        words_list = get_db("SELECT id, maori, english, description FROM words WHERE maori=? OR english=?", (query, query))
        if len(words_list) == 0:
            words_list = -1
        return render_template("home.html", words_list=words_list)
    else:
        return render_template("home.html")


@app.route('/word/<word_id>')
def show_word(word_id):
    """
    This function gets the details of a word so the user can display it.
    :arg word_id: the ID of the word that needs to be displayed
    :return: the details of the word
    """
    query = """SELECT words.id, words.maori, words.english, words.description, 
    words.level, categories.category, words.image, words.date, users.username
    FROM ((words 
    INNER JOIN categories ON words.category=categories.id)
    INNER JOIN users ON words.user=users.id)
    WHERE words.id=?"""
    word_list = get_db(query, (int(word_id), ), "one")
    word_list = list(word_list)
    # Changes the time to human-readable time
    word_list[7] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(word_list[7]))
    return render_template("ShowWord.html", word=word_list)


@app.route('/words/<cat_id>')
def words(cat_id):
    """
    This function gets the all the words or the words in a specific category
    from the 'words' database.
    :arg cat_id: The specific category that the user wants. If
    cat_id='all', then get all the words. If cat_id=1, then get all
    the words in that category.
    :return: the information of all the words
    """
    categories = get_db("SELECT * FROM categories")
    if cat_id == "all":  # If the user wants all the words
        words_list = get_db("SELECT id, maori, english, description FROM words")
    else:
        words_list = get_db("SELECT id, maori, english, description FROM words WHERE category = ?", (cat_id,))

    return render_template("words.html", categories=categories, words_list=words_list)


@app.route('/delete_word/', methods=['POST'])
@app.route('/delete_word/<word_id>', methods=['GET'])
def delete_word(word_id=None):
    """
    This function deletes a word from the database.
    :arg word_id: the ID of the word that needs to be deleted
    :return:
        For POST, this function deletes the word in the database
        using the ID provided and returns the Words HTML page.
        For GET, this function returns the confirm page to delete.
    """
    if 'teacher' in session:
        if request.method == "POST":
            exec_db("DELETE FROM words WHERE id=?", (session["DeleteWord_temp"], ))
            del session["DeleteWord_temp"]
            return redirect(url_for('words', cat_id='all'))
        else:
            session["DeleteWord_temp"] = word_id  # Saves the word_id for the real deletion
            return render_template("DeleteWord.html")
    else:
        return render_template("PleaseLogin.html")


@app.route('/add_word/', methods=['POST', 'GET'])
def add_word():
    """
    This function adds a word into the database. It saves the image and
    inserts all the relevant details of the word to the database.
    I have not used get_db() and exec_db() functions because I am
    executing mutiple SQL queries, which means it would be inefficient to open
    and close the database mutiple times.
    :return:
        For POST, this function returns the Show Word page where it shows
        the details of the word just added
        For GET, this function returns the HTML page that provides all the inputs.
    """
    if 'teacher' in session:
        if request.method == "POST":
            # Below code collects all the information of the word
            maoriword = request.form.get('maoriword').strip().lower()
            englishword = request.form.get('englishword').strip().lower()
            description = request.form.get('description').strip()
            level = int(request.form.get('level').strip())
            category = int(request.form.get('category'))
            image = request.files['image']

            con = sqlite3.connect(DATABASE)
            cur = con.cursor()

            cur.execute("SELECT id FROM words WHERE maori=?", (maoriword, ))
            exist = cur.fetchone()
            if exist is not None:  # Checks if word already exists
                cur.execute("SELECT * FROM categories")
                categories = cur.fetchall()
                return render_template("AddWord.html", categories=categories, error=True)

            query = "INSERT INTO words (maori, english, description, level, category, image, date, user) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            try:
                image.save(os.path.join(UPLOAD_FOLDER, image.filename))  # Saves the image to the server
                cur.execute(query, (maoriword, englishword, description, level, category, image.filename,
                                    time.time(), session['user']))
                con.commit()
            except:
                return render_template("fail.html")

            cur.execute("SELECT id FROM words WHERE maori=?", (maoriword,))
            word_id = cur.fetchone()[0]
            con.close()
            return redirect(url_for('show_word', word_id=word_id))
        else:
            categories = get_db("SELECT * FROM categories")
            return render_template("AddWord.html", categories=categories)
    else:
        return render_template("PleaseLogin.html")


@app.route('/modify_word/<word_id>', methods=['POST', 'GET'])
def modify_word(word_id=None):
    """
    This function modifies a word into the database. It updates the image if
    necessary and updates all the relevant details of the word to the database.
    :return:
        For POST, this function returns the Show Word page where it shows
        the details of the word just added
        For GET, this function returns the HTML page that provides all the inputs.
    """
    if 'teacher' in session:
        if request.method == "POST":
            englishword = request.form.get('englishword').strip().lower()
            description = request.form.get('description').strip()
            level = int(request.form.get('level').strip())
            category = int(request.form.get('category'))
            image = request.files['image']

            try:
                if image:
                    query = "UPDATE words SET english=?, description=?, level=?, category=?, image=? WHERE id=?;"

                    image.save(os.path.join(UPLOAD_FOLDER, image.filename))  # Saves the image to the server
                    exec_db(query, (englishword, description, level, category, image.filename, word_id))
                else:
                    query = "UPDATE words SET english=?, description=?, level=?, category=? WHERE id=?"
                    exec_db(query, (englishword, description, level, category, word_id))
            except:
                return render_template("fail.html")

            return redirect(url_for('show_word', word_id=word_id))
        else:
            categories = get_db("SELECT * FROM categories")
            word = get_db("SELECT * FROM words WHERE id=?", (word_id, ), "one")
            return render_template("ModifyWord.html", categories=categories, word=word)
    else:
        return render_template("PleaseLogin.html")


@app.route('/cats/')
def cats():
    """
    This function gets the all the categories from the 'categories' database.
    :return: returns the categories with the relevant HTML page
    """

    # This SQL query selects two databases, words and categories, and collect
    # all the categories and number of words in that category.
    categories = get_db(
    """SELECT categories.id, categories.category, COUNT(words.id) FROM categories
    LEFT JOIN words ON words.category=categories.id
    GROUP BY categories.id""")

    return render_template("categories.html", categories=categories)



@app.route('/delete_cat/', methods=['POST'])
@app.route('/delete_cat/<cat_id>', methods=['GET'])
def delete_cat(cat_id=None):
    """
    This function deteles a category from the database
    :arg word_id: the ID of the category that needs to be deleted
    :return:
        For POST, this function deletes the category using the ID provided
        in the database and returns the Words HTML page.
    """
    if 'teacher' in session:
        if request.method == "POST":
            exec_db("UPDATE words SET category=0 WHERE category=?", (session["DeleteCat_temp"], ))
            exec_db("DELETE FROM categories WHERE id=?", (session["DeleteCat_temp"], ))
            del session["DeleteCat_temp"]
            return redirect(url_for('cats'))
        else:
            cat = get_db("SELECT id FROM words WHERE id=?", (cat_id,))

            session["DeleteCat_temp"] = cat_id  # Saves the cat_id for the real deletion
            return render_template("DeleteCat.html", num=len(cat))
    else:
        return render_template("PleaseLogin.html")


@app.route('/add_cat/', methods=['GET', 'POST'])
def add_cat():
    """
    This function adds a category into the database.
    :return:
        For POST, this function returns the category page
        where it shows all the categories.
        For GET, this function returns the HTML page that provides all the inputs.
    """
    if 'teacher' in session:
        if request.method == "POST":
            cat = request.form.get('add').strip().title()
            exist_cat = get_db("SELECT id FROM categories WHERE category=?", (cat,), "one")

            if exist_cat is not None:  # Checks if category already exists
                return render_template('AddCat.html', error=True)

            exec_db("INSERT INTO categories (category) VALUES (?)", (cat, ))
            return redirect(url_for('cats'))
        else:
            categories = get_db("SELECT * FROM categories")
            return render_template('AddCat.html', categories=categories)
    else:
        return render_template("PleaseLogin.html")


@app.route('/modify_cat/<cat_id>', methods=['GET', 'POST'])
def modify_cat(cat_id):
    if 'teacher' in session:
        if request.method == "POST":
            cat = request.form.get('modify').strip().title()

            exec_db("UPDATE categories SET category=? WHERE id=?", (cat, cat_id, ))
            return redirect(url_for('cats'))
        else:
            category = get_db("SELECT * FROM categories WHERE id=?", (cat_id, ), "one")
            return render_template('ModifyCat.html', category=category)
    else:
        return render_template("PleaseLogin.html")


@app.route('/logout')
def logout():
    """
    This function logs the user out by clearing the sessions.
    :return: returns the redirect to homepage
    """
    session.clear()
    return redirect(url_for('home'))


@app.route('/login', methods=['POST', 'GET'])
def login():
    """
    This funtion logs the user in by checking the whether the user exist
    and the password is correct.
    :return:
        For POST, it returns the homepage if the user logs in successfully and
        the user ID and the role(student or teacher) is saved in the session, otherwise
        it returns the error created.
        For GET, it returns the login page.
    """
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']
        query = "SELECT id, password, role FROM users WHERE username=?"
        user = get_db(query, (username, ), "one")

        if user is None:  # Check if the username is correct
            return render_template("login.html", uerror=True)
        elif hashlib.sha256(password.encode("utf-8")).hexdigest() != user[1]:  # Check if the password is correct
            return render_template("login.html", perror=True)

        # Saves the ID and the role to the session
        session['user'] = user[0]
        if user[2]:
            session['teacher'] = True

        return redirect(url_for('home'))
    return render_template("login.html")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    """
    This funtion registers the users, which collects their information such as
    their first name and last name.
    I have also not used get_db() and exec_db() similar to the reason
    mentioned in add_word()
    :return:
        For POST, it returns the homepage if the user is registered successfully and
        after the user and role(student or teacher) is saved in the session, otherwise
        it returns the error created.
        For GET, it returns the signup page.
    """
    if request.method == 'POST':
        # Below code collects all the information of the user
        firstname = request.form.get('firstname').strip().title()
        lastname = request.form.get('lastname').strip().title()
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        role = int(request.form.get('role'))
        print(request.form)

        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        cerror = -1
        uerror = False
        eerror = False

        # Check if the user is actually a teacher
        if role == 1:
            check = request.form.get('check')
            if check == TEACHER_CODE:
                cerror = 0
            else:
                cerror = 1

        # Check is username is taken
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        exist_user = cur.fetchone()
        if exist_user is not None:
            uerror = True

        # Check if email is used
        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        exist_email = cur.fetchone()
        if exist_email is not None:
            eerror = True

        if uerror or eerror or cerror == 1:
            return render_template("signup.html", cerror=cerror, uerror=uerror, eerror=eerror)

        query = "INSERT INTO users (firstname, lastname, username, email, password, role) VALUES (?, ?, ?, ?, ?, ?)"
        # I have used hashlib because it is easier to use and builtin in Python
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        try:
            cur.execute(query, (firstname, lastname, username, email, hashed_password, role))
            con.commit()
        except:
            return render_template("fail.html")

        # Find the ID of the new added user and saves it into session
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        session['user'] = user[0]
        if role == 1:
            session['teacher'] = True
        con.close()

        return redirect(url_for('home'))

    return render_template("signup.html")


if __name__ == '__main__':
    app.run() 

