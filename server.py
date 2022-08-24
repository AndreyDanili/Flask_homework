from __future__ import annotations
import typing
import pydantic
from flask import Flask, jsonify, request
from flask.views import MethodView
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, func, create_engine


class HttpError(Exception):

    def __init__(self, status_code: int, message: str | dict | list):
        self.status_code = status_code
        self.message = message


class CreateAdvertisement(pydantic.BaseModel):
    header: str
    description: str
    author: str


class PatchAdvertisement(pydantic.BaseModel):
    header: typing.Optional[str]
    description: typing.Optional[str]
    author: typing.Optional[str]


def validate(model, raw_data: dict):
    try:
        return model(**raw_data).dict()
    except pydantic.ValidationError as error:
        raise HttpError(400, error.errors())


app = Flask('app')


@app.errorhandler(HttpError)
def http_error_handler(error: HttpError):
    response = jsonify({
        'status': 'error',
        'reason': error.message
    })
    response.status_code = error.status_code
    return response


app.config['JSON_AS_ASCII'] = False

PG_DSN = 'postgresql://admin:admin1pwd@postgresdb/advertisement'

engine = create_engine(PG_DSN)
Session = sessionmaker(bind=engine)

Base = declarative_base()


class Advertisement(Base):
    __tablename__ = 'advertisement'
    id = Column(Integer, primary_key=True)
    header = Column(String, index=True, unique=True, nullable=False)
    description = Column(String, nullable=False)
    author = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


def get_advertisement(session: Session, advertisement_id: int):
    advertisement = session.query(Advertisement).get(advertisement_id)
    if advertisement is None:
        raise HttpError(404, 'Advertisement not found')
    return advertisement


Base.metadata.create_all(engine)


class AdvertisementView(MethodView):

    def get(self, advertisement_id: int):
        with Session() as session:
            advertisement = get_advertisement(session, advertisement_id)
            return jsonify({'header': advertisement.header,
                            'description': advertisement.description,
                            'author': advertisement.author,
                            'created_at': advertisement.created_at.isoformat()
                            }
                           )

    def post(self):
        validated = validate(CreateAdvertisement, request.json)

        with Session() as session:
            advertisement = Advertisement(
                                        header=validated['header'],
                                        description=validated['description'],
                                        author=validated['author']
                                        )
            session.add(advertisement)
            session.commit()
            return {'id': advertisement.id}

    def patch(self, advertisement_id: int):
        validated = validate(PatchAdvertisement, request.json)

        with Session() as session:
            advertisement = get_advertisement(session, advertisement_id)
            if validated.get('header'):
                advertisement.header = validated['header']
            if validated.get('description'):
                advertisement.description = validated['description']
            if validated.get('author'):
                advertisement.author = validated['author']
            session.add(advertisement)
            session.commit()
            return {'status': 'OK'}

    def delete(self, advertisement_id: int):
        with Session() as session:
            advertisement = get_advertisement(session, advertisement_id)
            session.delete(advertisement)
            session.commit()
            return {'status': 'OK'}


advertisement_view = AdvertisementView.as_view('advertisement')
app.add_url_rule('/advertisement/', view_func=advertisement_view, methods=['POST'])
app.add_url_rule('/advertisement/<int:advertisement_id>', view_func=advertisement_view, methods=['GET', 'PATCH', 'DELETE'])

app.run(host='0.0.0.0', port='5000')
