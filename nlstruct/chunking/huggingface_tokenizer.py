import re

import numpy as np
import pandas as pd
from tqdm import tqdm


def huggingface_tokenize(docs, tokenizer, with_tqdm=False, **kwargs):
    doc_ids = []
    tokens = []
    begins = []
    ends = []
    token_idx = []
    special_tokens = [t for token in tokenizer.special_tokens_map.values() for t in ((token,) if isinstance(token, str) else token)]
    special_tokens += ["▁", "##", "</w>"]
    for doc_id, text in tqdm(zip(docs["doc_id"], docs["text"]), disable=not with_tqdm, total=len(docs), leave=False, desc="Tokenizing"):
        i = 0
        token_id = 0

        sentence_pieces = tokenizer.tokenize(text)
        tokenizer_output = tokenizer.encode_plus(tokenizer.convert_tokens_to_ids(sentence_pieces), return_special_tokens_mask=True)
        encoded_pieces = tokenizer.convert_ids_to_tokens(tokenizer_output["input_ids"])
        pieces = np.asarray(encoded_pieces)
        pieces[~np.asarray(tokenizer_output["special_tokens_mask"], dtype=bool)] = sentence_pieces
        for piece, encoded_piece in zip(pieces, encoded_pieces):
            doc_ids.append(doc_id)
            tokens.append(encoded_piece)
            striped_piece = piece
            for special in special_tokens:
                striped_piece = striped_piece.replace(special, "")
            piece_size = len(striped_piece)
            delta = len(re.search(r"^\s*", text[i:]).group(0))
            if striped_piece != text[i+delta:i+delta + piece_size]:
                raise Exception(f"Wordpiece tokenizer replaced {repr(text[i+delta:i+delta + piece_size])} (in {repr(text[i:i+delta + piece_size + 5])}) "
                                f"with {repr(striped_piece)} (or multiple pieces). "
                                f"You must perform substitutions before to ensure that this does not happen, otherwise wordpieces characters cannot be computed.")
            i += delta
            begins.append(i)
            i += piece_size
            ends.append(i)
            token_idx.append(token_id)
            token_id += 1
    tokens = pd.DataFrame({"doc_id": doc_ids, "token_id": range(len(token_idx)), "token_idx": token_idx, "token": tokens, "begin": begins, "end": ends})
    voc = tokenizer.convert_ids_to_tokens(list(range(tokenizer.vocab_size)))
    counts = {}
    for i, token in enumerate(list(voc)):
        counts[token] = counts.get(token, 0) + 1
        if counts[token] > 1:
            voc[i] = token + "-{}".format(i)
    token_voc = pd.CategoricalDtype(voc)
    tokens = tokens.astype({"doc_id": docs["doc_id"].dtype, "token": token_voc})
    return tokens
