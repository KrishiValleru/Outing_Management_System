import qrcode


def generate_qr_image(token):

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(token)

    qr.make(
        fit=True
    )

    return qr.make_image(
        fill_color="black",
        back_color="white"
    )