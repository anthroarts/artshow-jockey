let loadButton;
let saveButton;
let statusText;
let artistIdField;
let pieceIdField;
let locationSelect;
let buyNowCheckbox;
let bidderFields;
let bidFields;

document.addEventListener('DOMContentLoaded', () => {
  loadButton = document.getElementById('load');
  saveButton = document.getElementById('save');
  statusText = document.getElementById('status');
  artistIdField = document.getElementById('artist');
  pieceIdField = document.getElementById('piece');
  locationSelect = document.getElementById('location');
  buyNowCheckbox = document.getElementById('autobuy');
  bidderFields = document.getElementsByClassName('bidder');
  bidFields = document.getElementsByClassName('bid');

  loadButton.addEventListener('click', load);
  saveButton.addEventListener('click', save);
  artistIdField.addEventListener('input', () => {
    pieceIdField.value = '';
    clearFields();
  });
  pieceIdField.addEventListener('input', clearFields);
  locationSelect.addEventListener('input', setNotSaved);
  buyNowCheckbox.addEventListener('input', setNotSaved);
  buyNowCheckbox.addEventListener('input', toggleDisableOnNonBuyNowElements);
  for (var i = 0; i < bidderFields.length; ++i) {
    bidderFields[i].addEventListener('input', setNotSaved);
    bidFields[i].addEventListener('input', setNotSaved);
  }
});

function toggleDisableOnNonBuyNowElements() {
  const maybeDisabled = !!buyNowCheckbox.checked;
  const nFields = bidderFields.length;
  for (var i = 1; i < nFields; i++) {
    /* for every bidder but the first bidder */
    bidderFields[i].disabled = maybeDisabled;
    bidFields[i].disabled = maybeDisabled;
  }
  /* we still need the first bidder's bidder ID */
  bidFields[0].disabled = maybeDisabled;
}

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
    }
    if (length >= 1) {
      buyNowCheckbox.checked = json.bids[0].buy_now_bid;
    }

    while (locationSelect.firstChild) {
      locationSelect.removeChild(locationSelect.firstChild);
    }
    const emptyLocation = document.createElement('option');
    emptyLocation.value = '';
    emptyLocation.textContent = '---';
    locationSelect.appendChild(emptyLocation);
    for (let location of json['locations']) {
      const locationOption = document.createElement('option');
      locationOption.value = location;
      locationOption.textContent = location;
      if (location == json['location']) {
        locationOption.selected = true;
      }
      locationSelect.appendChild(locationOption);
    }

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
  buyNowCheckbox.classList.remove('error');

  for (var i = 0; i < bidderFields.length; ++i) {
    bidderFields[i].classList.remove('error');
    bidFields[i].classList.remove('error');
  }
}

function setNotSaved() {
  statusText.textContent = 'Unsaved changes.'
}

function clearFields() {
  for (var i = 0; i < bidderFields.length; ++i) {
    bidderFields[i].value = '';
    bidFields[i].value = '';
  }
  while (locationSelect.firstChild) {
    locationSelect.removeChild(locationSelect.firstChild);
  }
  const emptyLocation = document.createElement('option');
  emptyLocation.value = '';
  emptyLocation.textContent = '---';
  locationSelect.appendChild(emptyLocation);
  buyNowCheckbox.checked = false;
  statusText.textContent = '';
}

function load() {
  clearErrors();
  clearFields();

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
      if (bidFields[i].value !== '' || (i == 0 && buyNowCheckbox.checked)) {
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
        'buy_now_bid': i == 0 && buyNowCheckbox.checked,
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
    body: JSON.stringify({'bids': bids, 'location': locationSelect.value}),
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
