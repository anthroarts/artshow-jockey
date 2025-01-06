const supportedPrinters = [
    { vendorId: 0x0A5F, productId: 0x0015 },  // Zebra LP-2824
    { vendorId: 0x0A5F, productId: 0x00A3 },  // Zebra LP-2824 Plus
];

function isSupported(device) {
    for (const printer of supportedPrinters) {
        if (device.vendorId == printer.vendorId &&
            device.productId == printer.productId) {
            return true;
        }
    }
    return false;
}

let labelPrinterStatus;
let selectedDevice = null;

function setUpLabelPrinter(statusElementId) {
    labelPrinterStatus = document.getElementById(statusElementId);

    navigator.usb.getDevices().then((devices) => {
        for (const device of devices) {
            if (isSupported(device)) {
                selectedDevice = device;
                labelPrinterStatus.textContent = 'Label printer ready.';
            }
        }
    });

    navigator.usb.addEventListener('connect', (e) => {
        if (selectedDevice == null && isSupported(e.device)) {
            selectedDevice = e.device;
            labelPrinterStatus.textContent = 'Label printer ready.';
        }
    });

    navigator.usb.addEventListener('disconnect', (e) => {
        if (selectedDevice == e.device) {
            selectedDevice = null;
            labelPrinterStatus.textContent = 'Label printer disconnected.';
        }
    });
}

async function printLabels(data) {
    if (selectedDevice === null) {
        try {
            selectedDevice = await navigator.usb.requestDevice({ filters: supportedPrinters });
            labelPrinterStatus.textContent = 'Label printer ready.';
        } catch (e) {
            labelPrinterStatus.textContent = 'No printer selected.';
            return;
        }
    }

    await selectedDevice.open();

    try {
        await selectedDevice.selectConfiguration(1);
        await selectedDevice.claimInterface(0);

        let outEndpoint = undefined;
        for (const endpoint of selectedDevice.configuration.interfaces[0].alternate.endpoints) {
            if (endpoint.direction == 'out') {
                outEndpoint = endpoint;
                break;
            }
        }
        await selectedDevice.transferOut(outEndpoint.endpointNumber, new TextEncoder().encode(data));
    } finally {
        await selectedDevice.close();
    }
}
