let loadButton;
let saveButton;
let statusText;
let artistIdField;
let pieceIdField;
let locationField;
let bidderFields;
let bidFields;
let buyNowBidCheckboxes;

document.addEventListener('DOMContentLoaded', () => {
  loadButton = document.getElementById('load');
  saveButton = document.getElementById('save');
  statusText = document.getElementById('status');
  artistIdField = document.getElementById('artist');
  pieceIdField = document.getElementById('piece');
  locationField = document.getElementById('location');
  bidderFields = document.getElementsByClassName('bidder');
  bidFields = document.getElementsByClassName('bid');
  buyNowBidCheckboxes = document.getElementsByClassName('autobuy');

  loadButton.addEventListener('click', load);
  saveButton.addEventListener('click', save);
});

function updateBids(json, newStatus) {
  if ('error' in json) {
    if (json.error.field === 'artist_id') {
      artistIdField.classList.add('error');
    } else if (json.error.field === 'piece_id') {
      pieceIdField.classList.add('error');
    } else if (json.error.field === 'bidder') {
      bidderFields[json.error.index].classList.add('error');
    } else if (json.error.field === 'bid') {
      bidFields[json.error.index].classList.add('error');
    }

    statusText.textContent = json.error.message;
  } else {
    let length = Math.min(json.bids.length, bidderFields.length);
    for (var i = 0; i < length; ++i) {
      bidderFields[i].value = json.bids[i].bidder;
      bidFields[i].value = json.bids[i].bid;
      buyNowBidCheckboxes[i].checked = json.bids[i].buy_now_bid;
    }

    locationField.value = json['location']

    let lastUpdated = json['last_updated']
    if (lastUpdated === null)
      lastUpdated = 'Never'
    else
      lastUpdated = new Date(lastUpdated)
    statusText.textContent = 'Last updated: ' + lastUpdated;
  }
}

function clearErrors() {
  artistIdField.classList.remove('error');
  pieceIdField.classList.remove('error');

  for (var i = 0; i < bidderFields.length; ++i) {
    bidderFields[i].classList.remove('error');
    bidFields[i].classList.remove('error');
    buyNowBidCheckboxes[i].classList.remove('error');
  }
}

function load() {
  clearErrors();

  for (var i = 0; i < bidderFields.length; ++i) {
    bidderFields[i].value = '';
    bidFields[i].value = '';
    buyNowBidCheckboxes[i].checked = false;
  }
  locationField.value = '';

  statusText.textContent = 'Loading...';
  fetch(`../${artistIdField.value}/${pieceIdField.value}/`, {
    credentials: 'include',
    mode: 'cors',
    headers: {
      'Accept': 'application/json',
      'X-CSRFToken': Cookies.get('csrftoken'),
    }})
  .then(response => {
    if (response.ok)
      return response.json();
    else
      return Promise.reject(response.statusText);
  })
  .then(json => updateBids(json),
        error => statusText.textContent = 'Error: ' + error);
}

function save() {
  clearErrors();

  let foundEmpty = false;
  let error = null;
  let bids = [];

  for (var i = 0; i < bidderFields.length; ++i) {
    if (bidderFields[i].value === '') {
      foundEmpty = true;
      if (bidFields[i].value !== '' ||
          buyNowBidCheckboxes[i].checked) {
        bidderFields[i].classList.add('error');
        error = 'Missing bidder.';
        break;
      }
    } else {
      if (foundEmpty) {
        bidderFields[i].classList.add('error');
        error = 'Fill in bids in consecutive rows.';
        break;
      }

      if (bidFields[i].value === '') {
        bidFields[i].classList.add('error');
        error = 'Missing bid.';
        break;
      }

      bids.push({
        'bidder': bidderFields[i].value,
        'bid': bidFields[i].value,
        'buy_now_bid': buyNowBidCheckboxes[i].checked,
      });
    }
  }

  if (error !== null) {
    statusText.textContent = error;
    return;
  }

  statusText.textContent = 'Saving...';
  fetch(`../${artistIdField.value}/${pieceIdField.value}/`, {
    method: 'POST',
    body: JSON.stringify({'bids': bids, 'location': locationField.value}),
    credentials: 'include',
    mode: 'cors',
    headers: {
      'Accept': 'application/json',
      'X-CSRFToken': Cookies.get('csrftoken'),
    }})
  .then(response => {
    if (response.ok)
      return response.json();
    else
      return Promise.reject(response.statusText);
  })
  .then(json => updateBids(json),
        error => statusText.textContent = 'Error: ' + error);
}
