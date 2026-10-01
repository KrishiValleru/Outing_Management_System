let scanner = null;

let scannerRunning = false;


const resultBox = document.getElementById(
    "scan-result"
);

const resultTitle = document.getElementById(
    "result-title"
);

const resultMessage = document.getElementById(
    "result-message"
);

const scanAgainButton = document.getElementById(
    "scan-again"
);


function showResult(
    success,
    title,
    message
) {

    resultBox.className =
        success
            ? "scan-result success"
            : "scan-result error";

    resultTitle.textContent = title;

    resultMessage.innerHTML = message;

    scanAgainButton.style.display = "inline-block";
}


function extractToken(decodedText) {

    /*
     * Our QR currently contains the raw secure token.
     */
    return decodedText.trim();
}


async function verifyToken(token) {

    try {

        const response = await fetch(
            "/gate/verify",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    token: token
                })
            }
        );


        const data = await response.json();


        if (data.success) {

            showResult(
                true,
                "QR VERIFIED",
                `
                    <strong>Student:</strong>
                    ${data.student}
                    <br>

                    <strong>Leave Date:</strong>
                    ${data.date}
                    <br>

                    <strong>Leave Type:</strong>
                    ${data.leave_type}
                    <br><br>

                    Student is permitted to leave campus.
                `
            );

        } else {

            showResult(
                false,
                "QR REJECTED",
                data.message
            );
        }


    } catch (error) {

        console.error(error);

        showResult(
            false,
            "VERIFICATION ERROR",
            "Could not contact the server."
        );
    }
}


async function stopScanner() {

    if (
        scanner &&
        scannerRunning
    ) {

        try {

            await scanner.stop();

            scannerRunning = false;

        } catch (error) {

            console.error(
                "Could not stop scanner:",
                error
            );
        }
    }
}


async function startScanner() {

    resultBox.className =
        "scan-result";

    resultTitle.textContent = "";

    resultMessage.textContent = "";

    scanAgainButton.style.display =
        "none";


    scanner = new Html5Qrcode(
        "reader"
    );


    try {

        await scanner.start(

            {
                facingMode: "environment"
            },

            {
                fps: 10,

                qrbox: {
                    width: 250,
                    height: 250
                }
            },

            async (
                decodedText,
                decodedResult
            ) => {

                console.log(
                    "QR detected:",
                    decodedText
                );

                await stopScanner();

                const token =
                    extractToken(
                        decodedText
                    );

                await verifyToken(
                    token
                );
            },

            (errorMessage) => {

                // QR hasn't been detected yet.
                // This is normal and does not
                // need to be displayed.
            }

        );

        scannerRunning = true;

    } catch (error) {

        console.error(
            "Camera error:",
            error
        );

        showResult(
            false,
            "CAMERA ERROR",
            `
                Unable to access the camera.
                <br><br>
                Please allow camera permission
                and try again.
            `
        );
    }
}


scanAgainButton.addEventListener(
    "click",
    async () => {

        await startScanner();

    }
);


startScanner();