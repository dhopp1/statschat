import time


def parse_message(text):
    "parse the progress text into progress bar value and text"
    process_dict = {
        "Determining which tools to use...": {
            "overall_step": 1,
            "proportion": 0.00,
            "out_text": "(1/5) Determining which tools to use...",
        },
        "Transforming the data...": {
            "overall_step": 2,
            "proportion": 0.2,
            "out_text": "(2/5) Transforming the data...",
        },
        "Explaining the transformations...": {
            "overall_step": 3,
            "proportion": 0.4,
            "out_text": "(3/5) Explaining the transformations...",
        },
        "Generating commentary...": {
            "overall_step": 4,
            "proportion": 0.6,
            "out_text": "(4/5) Generating commentary...",
        },
        "Generating a visualization...": {
            "overall_step": 5,
            "proportion": 0.8,
            "out_text": "(5/5) Generating a visualization...",
        },
    }
    which_key = [x for x in process_dict.keys() if x in text]
    if len(which_key) > 0:
        which_key = which_key[0]
    else:
        return 0, "?"
    base_progress = process_dict[which_key]["proportion"]

    final_progress = int(base_progress * 100)

    # final text
    final_text = process_dict[which_key]["out_text"] + text.split(which_key)[1]

    return final_progress, final_text


class Logger(object):
    def __init__(self, status_progress, status_text):
        self.buffer = ""
        self.status_progress = status_progress
        self.status_text = status_text
        self.last_update = 0

    def write(self, message):
        # only write once per second
        if time.time() - self.last_update >= 1:
            progress_update, text_update = parse_message(message)
            if text_update != "?":
                self.status_progress = self.status_progress.progress(progress_update)
                self.status_text = self.status_text.markdown(text_update)
            self.last_update = time.time()

    def flush(self):
        pass

    def clear(self):
        self.status_progress = self.status_progress.empty()
        self.status_text = self.status_text.empty()
