from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
from colorthief import ColorThief
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# Read Google Books API key
try:
    with open('google_books_api_key.cfg', "r") as f:
        api_key = f.readline()
except:
    print("Place your Google Books API key as a single line in", os.getcwd()+"/google_books_api_key.cfg")
    exit()

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    shelves = db.relationship('Bookshelf', backref='user', lazy=True)

# Define a many-to-many relationship table
bookshelf_book_association = db.Table('bookshelf_book_association',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id')),
    db.Column('bookshelf_id', db.Integer, db.ForeignKey('bookshelf.id'))
)
    
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    author = db.Column(db.String(128), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    pub_date = db.Column(db.Date)
    genre = db.Column(db.String(64))
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(256))
    avg_rating = db.Column(db.Float, default=0.0)
    num_ratings = db.Column(db.Integer, default=0)

    # Relationship with Review Model
    reviews = db.relationship('Review', backref='book', lazy=True)
    
    # Establish a many-to-many relationship with bookshelves
    bookshelves = db.relationship('Bookshelf', secondary=bookshelf_book_association, back_populates='books')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user = db.relationship('User')

class Bookshelf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shelf_name = db.Column(db.String(50), nullable=False)
    books = db.relationship('Book', secondary=bookshelf_book_association, back_populates='bookshelves', lazy=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_password = request.form['password']

        # Check for existing user with the same email or username
        existing_user_email = User.query.filter_by(email=new_email.lower()).first()
        existing_user_username = User.query.filter_by(username=new_username.lower()).first()

        if existing_user_email:
            flash('Registration failed. Email already in use.', 'error')
        elif existing_user_username:
            flash('Registration failed. Username already in use.', 'error')
        else:
            # Create a new user
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            new_user = User(username=new_username, email=new_email.lower(), password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            # Log in the new user
            login_user(new_user)

            # Create default bookshelves for the new user
            default_shelves = ['To-Read', 'Currently Reading', 'Read']
            for shelf_name in default_shelves:
                new_shelf = Bookshelf(user_id=current_user.id, shelf_name=shelf_name)
                db.session.add(new_shelf)
            db.session.commit()

            flash('Registration successful. Welcome!', 'success')
            return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'email' not in request.form:
            flash('Email is required.', 'danger')
            return redirect(url_for('login'))

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            # Add your login logic here (e.g., setting a session variable)
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check your email and password.', 'danger')

    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    # Implement logout logic here if needed
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route("/")
@app.route("/home")
@login_required
def home():
    # Get the user's shelves and books
    user_shelves = current_user.shelves

    # Create a dictionary to store book covers and titles for each shelf
    shelf_books_info = {}

    for shelf in user_shelves:
        # Retrieve the books for each shelf
        shelf_books = shelf.books
        # Store book covers and titles in the dictionary
        shelf_books_info[shelf.shelf_name] = [{'id': book.id, 'cover': book.cover_image, 'title': book.title} for book in shelf_books]

    return render_template('home.html', user_shelves=user_shelves, shelf_books_info=shelf_books_info)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form['search_query']

        # Check if the book exists in your database by title or ISBN
        book = Book.query.filter((Book.title == search_query) | (Book.isbn == search_query)).first()

        if book:
            return redirect(url_for('book_detail', book_id=book.id))
        else:
            # Fetch book details from Google Books API
            book_data = fetch_book_data(search_query)

            if book_data:
                if 'isbn' in book_data:
                    # Check if the book with the same ISBN already exists
                    existing_book = Book.query.filter_by(isbn=book_data['isbn']).first()

                    if existing_book:
                        return redirect(url_for('book_detail', book_id=existing_book.id))

                    # Add the book to the database
                    new_book = Book(
                        title=book_data['title'],
                        author=book_data['author'],
                        isbn=book_data['isbn'],
                        pub_date=book_data['pub_date'],
                        genre=book_data['genre'],
                        description=book_data['description'],
                        cover_image=book_data['cover_image']
                    )

                    db.session.add(new_book)
                    db.session.commit()

                    return redirect(url_for('book_detail', book_id=new_book.id))
                else:
                    # Display a message for book not found
                    flash(f'This book could not be found.', 'error')
                    return redirect(url_for('home'))

    return redirect(url_for('home'))  # Redirect to home if accessed via GET request

# Function to fetch book details from Google Books API
def fetch_book_data(search_query):
    url = f'https://www.googleapis.com/books/v1/volumes?q={search_query}&key={api_key}'

    response = requests.get(url)
    data = response.json()

    if 'items' in data:
        book_info = data['items'][0]['volumeInfo']

        title = book_info.get('title', 'N/A')
        author = ', '.join(book_info.get('authors', ['N/A']))
        isbn = book_info.get('industryIdentifiers', [{}])[0].get('identifier', 'N/A')
        
        # Check if the book with the same ISBN already exists
        existing_book = Book.query.filter_by(isbn=isbn).first()
        if existing_book:
            return {
                'title': existing_book.title,
                'author': existing_book.author,
                'isbn': existing_book.isbn,
                'pub_date': existing_book.pub_date,
                'genre': existing_book.genre,
                'description': existing_book.description,
                'cover_image': existing_book.cover_image
            }
        
        # Handle different date formats or missing dates
        pub_date_str = book_info.get('publishedDate', None)
        pub_date = parse_published_date(pub_date_str)
        
        genre = ', '.join(book_info.get('categories', ['N/A']))
        description = book_info.get('description', 'N/A')
        cover_image = book_info.get('imageLinks', {}).get('thumbnail', 'N/A')

        return {
            'title': title,
            'author': author,
            'isbn': isbn,
            'pub_date': pub_date,
            'genre': genre,
            'description': description,
            'cover_image': cover_image
        }

    return None


# Function to parse different date formats or handle missing dates
def parse_published_date(pub_date_str):
    if pub_date_str:
        try:
            # Attempt to parse the date with the expected format
            return datetime.strptime(pub_date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Attempt to parse the date with a different format
                return datetime.strptime(pub_date_str, '%Y').date()
            except ValueError:
                # Handle cases where the date cannot be parsed
                return None
    else:
        # Handle cases where the date is not present
        return None

@app.route('/book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def book_detail(book_id):
    # Retrieve the book from the database
    book = Book.query.get(book_id)
    # Load the users who wrote reviews as well
    reviews = Review.query.filter_by(book_id=book.id).join(User).all()

    if not book:
        # Display a message for book not found
        flash(f'This book could not be found.', 'error')
        return redirect(url_for('home'))

    # Get the user's shelves
    user_shelves = current_user.shelves
    
    # Calculate average rating and number of ratings
    average_rating, num_ratings = calculate_average_rating(book)
    
    # Extract colors from the cover image
    if book.cover_image:
        palette, text_colors = extract_colors(book)
    else:
        palette, text_colors = None, None

    # Check if the user has already reviewed this book
    user_review = Review.query.filter_by(user_id=current_user.id, book_id=book.id).first()
    
    # Handle the review form submission
    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')

        # If the user has already reviewed, update the existing review
        if user_review:
            user_review.rating = rating
            user_review.comment = comment
        else:
            # Create a new review
            new_review = Review(rating=rating, comment=comment, user_id=current_user.id, book_id=book.id)
            db.session.add(new_review)

        db.session.commit()
        flash('Review submitted successfully.', 'success')
        return redirect(url_for('book_detail', book_id=book.id))

    # Also load the reviewing user
    if user_review:
        user_review.user = current_user
    
    return render_template('book_detail.html', book=book, user_shelves=user_shelves, reviews=reviews, user_review=user_review, average_rating=average_rating, num_ratings=num_ratings, palette=palette, text_colors=text_colors)

def extract_colors(book):
    if book.cover_image == "N/A":
        return None, None
    
    image_path = f"static/images/{book.id}.jpg"
    
    if not os.path.exists(image_path):
        image_url = book.cover_image
        image_data = requests.get(image_url).content

        with open(image_path, "wb") as f:
            f.write(image_data)

    # Extract colors from the local cover image
    if os.path.exists(image_path):
        color_thief = ColorThief(image_path)
        palette = color_thief.get_palette(color_count=3)
        text_colors = [get_contrast_color(color) for color in palette]
    
    return palette, text_colors

def calculate_luminance(color):
    # Calculate luminance using the relative luminance formula
    r, g, b = color
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance

def get_contrast_color(background_color):
    # Choose white or black text color based on the luminance of the background color
    luminance = calculate_luminance(background_color)
    return 'black' if luminance > 128 else 'white'

@app.route('/move_to_shelf/<int:book_id>', methods=['POST'])
@login_required
def move_to_shelf(book_id):
    book = Book.query.get(book_id)
    shelf_id = request.form['shelf_id']

    if book and shelf_id:
        if shelf_id == "remove_from_all":
	        # Remove the book from all user's shelves
	        for user_shelf in current_user.shelves:
	            if book in user_shelf.books:
	                user_shelf.books.remove(book)
	        db.session.commit()
	        flash('The book has been removed from all your shelves.', 'success')
	        return redirect(url_for('book_detail', book_id=book_id))
        else:
            shelf = Bookshelf.query.get(shelf_id)

		    # Check if the book and shelf belong to the current user
            if shelf and shelf.user_id == current_user.id:
                # Remove the book from the user's other shelves
                for user_shelf in current_user.shelves:
                    if book in user_shelf.books:
                        user_shelf.books.remove(book)

                # Add the book to the selected shelf
                shelf.books.append(book)
                db.session.commit()
                flash(f'The book has been moved to the "{shelf.shelf_name}" shelf.', 'success')
                return redirect(url_for('book_detail', book_id=book_id))
            else:
                flash('Invalid shelf selection.', 'error')
                return redirect(url_for('book_detail', book_id=book_id))
    # Redirect to an error page or handle the case when the move fails
    flash('Could not move book to shelf.', 'error')
    return redirect(url_for('home'))

@app.route('/delete_review/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    review = Review.query.get(review_id)

    if review:
        # Check if the review belongs to the current user
        if review.user_id == current_user.id:
            # Delete the review
            db.session.delete(review)
            db.session.commit()
            flash('Review deleted successfully.', 'success')
        else:
            flash('You do not have permission to delete this review.', 'error')
    else:
        flash('Review not found.', 'error')

    # Redirect to the book detail page after deletion
    return redirect(url_for('book_detail', book_id=review.book_id))

# Add this function to your Flask app
def calculate_average_rating(book):
    total_ratings = 0
    num_ratings = 0

    for review in book.reviews:
        total_ratings += review.rating
        num_ratings += 1

    average_rating = total_ratings / num_ratings if num_ratings > 0 else 0

    return average_rating, num_ratings

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

