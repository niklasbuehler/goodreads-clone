Basic Goodreads Clone
===

This is a very basic Goodreads clone, built with Python Flask.

## Installation

1. Install all requirements with `pip install -r requirements.txt`.

2. Make sure to place your Google Books API key in `google_books_api_key.cfg`.

3. Then, simply run with `python app.py`.

## Roadmap

- [X] User Registration
  - [X] Basic user sign-up and login functionality
- [X] Responsive Design
- [X] Book Database
  - [X] Automatically grab unknown books from the Google Books API and lazily build a local database
  - [X] Include essential book details: title, cover, ISBN, author, genre, description
- [X] User Interaction
  - [X] Ability to add/remove books to/from a personal shelves
  - [X] Simple rating and review system for books
- [ ] Import / Export
  + [ ] Import shelves from Goodreads
  + [ ] Export to org mode
  + [ ] Import Kindle clippings
- [ ] Offer a selection of search results
- [ ] User Profiles
  + [ ] Show (public) shelves
  + [ ] Show ratings & reviews
  + [ ] Show imported Kindle clippings
  + [ ] Show reading stats (books read this year/month)
- [ ] Author profiles
- [ ] Social Features
  - [ ] Basic social networking functionalities (follow/friend)
  - [ ] Activity feed (updates from friends, added/popular books in general)
  - [ ] Share reading progress and recommendations
- [ ] Recommendation System
  - [ ] Basic algorithm for suggesting books based on user preferences
  - [ ] Incorporate `https://nathanrooy.github.io/posts/2023-04-12/visual-book-recommender/`?
- [ ] Reading Challenges & Stats
  - [ ] Create and participate in reading challenges
- [ ] Notifications
  - [ ] Basic notification system for updates, recommendations and challenges
  - [ ] Email alerts for key activities
- [ ] Admin Panel?
- [ ] AI Tools
  + [ ] Summary from Kindle clippings?
