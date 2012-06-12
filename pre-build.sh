#!/bin/sh

# update po files
for i in po/*.po; do
    msgmerge --previous --update $i po/*.pot;
done
