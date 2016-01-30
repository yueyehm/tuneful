import os.path
import json

from flask import request, Response, url_for, send_from_directory
from werkzeug.utils import secure_filename
from jsonschema import validate, ValidationError

from . import models
from . import decorators
from tuneful import app
from .database import session
from .utils import upload_path

@app.route("/api/songs", methods=["GET"])
def songs_get():
    """ Get a list of songs """
    # Get the querystring arguments
    name_like = request.args.get("name_like")

    # Get and filter the posts from the database
    songs = session.query(models.Song)
    if name_like:
        songs = songs.filter(models.Song.name.contains(name_like))

    songs = songs.order_by(models.Song.id)

    # Convert the posts to JSON and return a response
    data = json.dumps([song.as_dictionary() for song in songs])
    return Response(data, 200, mimetype="application/json")
    
@app.route("/api/songs", methods=["POST"])
def songs_post():
    """ Add a new post """
    data = request.json
    
    # Try to validate data
    try:
        validate(data, song_schema)
    except ValidationError as error:
        data = {"message": error.message}
        return Response(json.dumps(data), 422, mimetype="application/json")
    # Checking file in the database
    fileInDB = session.query(models.File).get(data["file"]["id"])

    if not fileInDB:
        data = {"message": "Cannot find the file in database"}
        return Response(json.dumps(data), 404, mimetype="application/json")
        
    # Add the song to the database
    song = models.Song(file=fileInDB)
    session.add(song)
    session.commit()

    # Return a 201 Created, containing the post as JSON and with the
    # Location header set to the location of the post
    data = json.dumps(song.as_dictionary())
    headers = {"Location": url_for("songs_get")}
    return Response(data, 201, headers=headers,
                    mimetype="application/json")
                    
@app.route("/uploads/<filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(upload_path(), filename)    
    
@app.route("/api/files", methods=["POST"])
@decorators.require("multipart/form-data")
@decorators.accept("application/json")
def file_post():
    file = request.files.get("file")
    if not file:
        data = {"message": "Could not find file data"}
        return Response(json.dumps(data), 422, mimetype="application/json")

    filename = secure_filename(file.filename)
    db_file = models.File(filename=filename)
    session.add(db_file)
    session.commit()
    file.save(upload_path(filename))

    data = db_file.as_dictionary()
    return Response(json.dumps(data), 201, mimetype="application/json")

song_schema = {
    "properties": {
        "file" : {
            "type" : "object",
            "properties" : {
                "id": {
                    "type" : "number"
                    }
            }
        }
    },
    "required": ["file"]
}

