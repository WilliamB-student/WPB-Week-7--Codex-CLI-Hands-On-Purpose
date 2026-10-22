The purpose of this analysis is to determine if the year a property was constructed can be used to estimate the sale price of the property.

Date of Codex session 10/21/2026

The following modules are required for the python scripts in this repository: numpy, pandas, and matplotlib


In this analysis, I found that the year a property was constructed had an R^2 value of 0.31 to the sale price, which is a fairly weak correlation, though it is a correlation. That's not unexpected, since many other factors will go into the value of a house, apart from the year it's constructed.
Additionally, this first model I used was a linear model. Noting the curve in the data, I used an exponential model which produced an R^2 of 0.32 and a quadratic model with an R^2 of 0.38. Additionally, using a quadratic model that incorporated many features produced an R^2 of 0.82, a much stronger correlation.
Personally, I don't think it's surprising that neighborhood and square footage can be used to more reasonably approximate the value of a house. I think it's more interesting how the features of the prices made a quadratic model noticeably better. A depression in home prices for houses built during the 1930's scans as appropriate.
Finally, these are only correlations and no causal link is found between these factors and home prices from this analysis. Further investigation would likely question whether continuing to use just the year constructed in isolation should be continued, and if so does using a quadratic model lead to a significant (>0.05) improvement in the model performance.
