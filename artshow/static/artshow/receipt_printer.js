const supportedPrinters = [
    { vendorId: 1208, productId: 514 },  // Epson TM-T88V
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

let receiptPrinterStatus;
let selectedDevice = null;

function setUpReceiptPrinter(statusElementId) {
  receiptPrinterStatus = document.getElementById(statusElementId);

    navigator.usb.getDevices().then((devices) => {
        for (const device of devices) {
            if (isSupported(device)) {
                selectedDevice = device;
                receiptPrinterStatus.textContent = 'Receipt printer ready.';
            }
        }
    });

    navigator.usb.addEventListener('connect', (e) => {
        if (selectedDevice == null && isSupported(e.device)) {
            selectedDevice = e.device;
            receiptPrinterStatus.textContent = 'Receipt printer ready.';
        }
    });

    navigator.usb.addEventListener('disconnect', (e) => {
        if (selectedDevice == e.device) {
            selectedDevice = null;
            receiptPrinterStatus.textContent = 'Receipt printer disconnected.';
        }
    });
}

async function printReceipt(data) {
    if (selectedDevice === null) {
        try {
            selectedDevice = await navigator.usb.requestDevice({ filters: supportedPrinters });
        } catch (e) {
            receiptPrinterStatus.textContent = 'No printer selected.';
            return;
        }
    }

    await selectedDevice.open();

    try {
        await selectedDevice.selectConfiguration(1);
        await selectedDevice.claimInterface(0);
        await selectedDevice.transferOut(1, data);
    } finally {
        await selectedDevice.close();
    }
}
