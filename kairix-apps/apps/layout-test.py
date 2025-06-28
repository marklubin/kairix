
from rich import print
from rich.layout import Layout


def main():
    layout = Layout()

    layout.split_column(
        Layout(name="logs"),
        Layout(name="response_status")

    )



    layout['response_status'].split_row(
        Layout(name="input"),
        Layout(name ="inference"),
        Layout(name= "tts")
    )


    print(layout)



if __name__ == "__main__":
    main()
