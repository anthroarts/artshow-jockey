from django.contrib.auth.models import User
from names_generator import generate_name
import random

from .models import Allocation, Artist, Bid, Bidder, BidderId, Location, Piece, Space
from peeps.models import Person


def distribution(max):
    population = range(1, max + 1)
    weights = reversed(range(1, max + 1))
    return random.choices(population, weights=weights)[0]


def create(email):
    # Create 99 artists
    artist_users = [
        User(username=f'artist{i}', email=email.replace('@', f'+artist{i}@'))
        for i in range(1, 100)
    ]
    artist_users = User.objects.bulk_create(artist_users)

    artist_people = [
        Person(user=user, email=user.email, email_confirmed=True, name=generate_name(style='capital'))
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

    # Create pieces and place them in locations
    spaces = Space.objects.all()
    for space in spaces:
        space.available = 0

    allocations = []
    pieces = []
    locations = []

    for artist in artists:
        allocation_map = {}
        num_spaces = distribution(6)
        piece_id = 1
        for _ in range(num_spaces + 1):
            space = random.choice(spaces)
            space.available += 1

            if space.pk not in allocation_map:
                allocation = Allocation(artist=artist, space=space, requested=1)
                allocations.append(allocation)
                allocation_map[space.pk] = allocation
            else:
                allocation_map[space.pk].requested += 1

            location = Location(
                type=space,
                name=f'{chr(space.pk + ord('A') - 1)}{space.available}',
                artist_1=artist,
            )
            locations.append(location)

            num_pieces = distribution(10)
            for _ in range(num_pieces + 1):
                pieces.append(Piece(
                    artist=artist,
                    pieceid=piece_id,
                    code=f'{artist.artistid}-{piece_id}',
                    name=generate_name(style='capital'),
                    min_bid=10,
                    status=Piece.StatusInShow,
                    location=location.name,
                    adult=location.name.startswith('A'),
                ))
                piece_id += 1

    spaces.bulk_update(spaces, ['available'])
    allocations = Allocation.objects.bulk_create(allocations)
    pieces = Piece.objects.bulk_create(pieces)
    locations = Location.objects.bulk_create(locations)

    # Create 500 bidders
    bidder_users = [User(username=f'bidder{i}', email=email.replace('@', f'+bidder{i}@')) for i in range(500)]
    bidder_users = User.objects.bulk_create(bidder_users)

    bidder_people = [
        Person(user=user, email=user.email, email_confirmed=True, name=generate_name(style='capital'))
        for user in bidder_users
    ]
    bidder_people = Person.objects.bulk_create(bidder_people)

    bidders = [Bidder(person=person) for person in bidder_people]
    bidders = Bidder.objects.bulk_create(bidders)

    bidder_ids = [BidderId(id=str(i).zfill(4), bidder=bidder) for i, bidder in enumerate(bidders, start=1)]
    BidderId.objects.bulk_create(bidder_ids)

    # Create bids
    bids = []
    for piece in pieces:
        num_bids = distribution(6)
        bid = piece.min_bid
        for _ in range(num_bids + 1):
            bidder = random.choice(bidders)
            bidder_id = bidder.bidderid_set.first()
            bids.append(Bid(piece=piece, bidder=bidder, amount=bid, bidderid=bidder_id))
            bid += 10
    Bid.objects.bulk_create(bids)
