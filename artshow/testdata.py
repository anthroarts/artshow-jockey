from django.contrib.auth.models import User
from names_generator import generate_name
import random

from .models import Artist, Bid, Bidder, BidderId, Piece
from peeps.models import Person


def create(email):
    # Create 99 artists
    artist_users = [
        User(username=f'artist{i}', email=email.replace('@', f'+artist{i}@'))
        for i in range(1, 100)
    ]
    artist_users = User.objects.bulk_create(artist_users)

    artist_people = [
        Person(user=user, email=user.email, name=generate_name(style='capital'))
        for user in artist_users
    ]
    artist_people = Person.objects.bulk_create(artist_people)

    artists = []
    for i, person in enumerate(artist_people, start=1):
        publicname = ""
        if bool(random.getrandbits(1)):
            publicname = generate_name(style='capital')
        artists.append(Artist(person=person, artistid=i, publicname=publicname))
    artists = Artist.objects.bulk_create(artists)

    # Create pieces for artists
    pieces = []
    for artist in artists:
        num_pieces = random.randint(1, 25)
        for i in range(1, num_pieces + 1):
            pieces.append(Piece(
                artist=artist,
                pieceid=i,
                code=f'{artist.artistid}-{i}',
                name=generate_name(style='capital'),
                min_bid=10,
                status=Piece.StatusInShow,
                location="A1"
            ))
    pieces = Piece.objects.bulk_create(pieces)

    # Create 500 bidders
    bidder_users = [User(username=f'bidder{i}', email=email.replace('@', f'+artist{i}@')) for i in range(500)]
    bidder_users = User.objects.bulk_create(bidder_users)

    bidder_people = [
        Person(user=user, email=user.email, name=generate_name(style='capital'))
        for user in bidder_users
    ]
    bidder_people = Person.objects.bulk_create(bidder_people)

    bidders = [Bidder(person=person) for person in bidder_people]
    bidders = Bidder.objects.bulk_create(bidders)

    bidder_ids = [BidderId(id=str(i).zfill(4), bidder=bidder) for i, bidder in enumerate(bidders, start=1)]
    BidderId.objects.bulk_create(bidder_ids)

    # Create 5000 bids
    bids = []
    for i in range(1, 5001):
        piece = pieces[i % len(pieces)]
        bidder = bidders[i % len(bidders)]
        bidder_id = bidder.bidderid_set.first()
        if bidder_id:
            bids.append(Bid(piece=piece, bidder=bidder, amount=i, bidderid=bidder_id))
    Bid.objects.bulk_create(bids)
