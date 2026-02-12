# web-editor

![GitHub License](https://img.shields.io/github/license/hviovn/web-editor)
![GitHub Release](https://img.shields.io/github/v/release/hviovn/web-editor)

Flask App to edit the dictionary for a specific language in the browser and then create a new timeline.

## Edit in the Browser

The dictionary for the [timeline project](https://github.com/hviovn/timeline) has grown over time. But with the introduction of categories the 571 entries can be easier organized and translated. The categories are:

- **Text** (175 lines)
- **Bible** quotes or names (189)
- **B9** are names, numbers and labels from Appendix B9 of the NWT (31)
- **A6-A** and **A6-B** are names of kings and prophets from Appendix A6 (55)
- **Wikipedia** articles with the same name might exist in other languages. With an API this translation can be checked or refined (44)
- **Timespan** includes simple strings 1368-1644, spans with label like 319 – 550 C.E. or 1943 – 1513 B.C.E. (31)
- **Other** has some deprecated strings (32), floats and a direct reference of a scripture

Now it would be nice, if one could see reference translations from Google, Bing, ChatGPT and Gemini3 and then just in a web browser could confirm the best translation. Especially the 175 first text lines requrie a native speaker, and this would make it so much easier.

## Submit a Pull request

That's where you loose 98% of normal people that might be able to help you. Instead, give them a button to change and have a final "Submit". Done. Write the code in Python for the rest. That's what I intend to do.
