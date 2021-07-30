#!/usr/bin/env sh

cd -- "$(git rev-parse --show-toplevel)" &&
	git archive HEAD --format=zip -o "RefoldEase_$(git branch --show-current).ankiaddon"
