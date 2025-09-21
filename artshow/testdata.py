from django.contrib.auth.models import User

from .models import Artist, Bid, Bidder, BidderId, Piece
from peeps.models import Person


def create(email):
    # Create 99 artists
    artist_users = [
        User(username=f'artist{i}', email=email.replace('@', f'+artist{i}@'))
        for i in range(2, 101)
    ]
    artist_users = User.objects.bulk_create(artist_users)

    artist_people = [Person(user=user) for user in artist_users]
    artist_people = Person.objects.bulk_create(artist_people)

    artists = [Artist(person=person, artistid=i) for i, person in enumerate(artist_people, start=2)]
    artists = Artist.objects.bulk_create(artists)

    # Create pieces for artists
    pieces = []
    for artist in artists:
        pieces.append(Piece(
            artist=artist,
            pieceid=1,
            name=f"Masterpiece by {artist.artistname()}",
            min_bid=10,
            status=Piece.StatusInShow,
            location="A1"
        ))
    pieces = Piece.objects.bulk_create(pieces)

    # Create 500 bidders
    bidder_users = [User(username=f'bidder{i}', email=f'bidder{i}@example.com') for i in range(1, 501)]
    bidder_users = User.objects.bulk_create(bidder_users)

    bidder_people = [Person(user=user) for user in bidder_users]
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
