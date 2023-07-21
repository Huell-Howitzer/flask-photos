from application.app import db

tags = db.Table('tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
    db.Column('photo_id', db.Integer, db.ForeignKey('photo.id'), primary_key=True)
)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tags = db.relationship('Tag', secondary=tags, lazy='subquery',
    backref=db.backref('photos', lazy=True))
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Photo %r>' % self.filename

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
