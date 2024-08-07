from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# For adding profile images to the comment section
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES

# TODO: Create a User table for all your registered users.
class User(UserMixin, db.Model):
    __tablename__ = "blog_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="commentator")


# TODO: Create a Blog table for all your posts.
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Create Foreign Key, "blog_users.id" the blog_users refers to the tablename of User.
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_users.id"))
    # Create reference to the User object. The "posts" refers to the posts property in the User class.
    author = relationship(User, back_populates="posts")

    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    post_comments = relationship("Comment", back_populates="reviews")


# TODO: Create a Comment table for all your comments.
class Comment(db.Model):
    __tablename__ = "blog_comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Child of User
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_users.id"))
    commentator = relationship(User, back_populates='comments')
    # Child of BlogPost
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    reviews = relationship(BlogPost, back_populates='post_comments')


def admin_decorator(function):
    @wraps(function)
    @login_required  # prevent -> AttributeError: 'AnonymousUserMixin' object has no attribute 'id'
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)

    return decorated_function


with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if not user:
            hash_salt = generate_password_hash(form.password.data, salt_length=8)
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                password=hash_salt
            )
            db.session.add(new_user)
            db.session.commit()
            # This line will authenticate the user with Flask-Login
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
    return render_template("register.html", pform=form, logged=current_user.is_authenticated)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if not user:
            flash("The email does not exist, please try again")
        elif not check_password_hash(user.password, form.password.data):
            flash("Incorrect password, please try again.")
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template('login.html', sform=form, logged=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, logged=current_user.is_authenticated)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=['GET','POST'])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    new_comment = CommentForm()
    if new_comment.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                body=new_comment.comment_text.data,
                commentator=current_user,
                reviews=requested_post,
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('get_all_posts'))
        flash("Please Login or register to comment")
        return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, logged=current_user, form=new_comment)


# TODO: Use a decorator so only an admin user can create a new post

@app.route("/new-post", methods=["GET", "POST"])
@admin_decorator
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_decorator
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_decorator
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html", logged=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged=current_user.is_authenticated)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
