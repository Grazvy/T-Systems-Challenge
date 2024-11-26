import matplotlib.pyplot as plt

# Data lists
loss1 = [3219157.550493392, 2732000, 3626000, 2128000, 2446000, 3536000, 2710000, 3930000, 4232000, 4292000,
         3220380.605176285, 2970000, 3726000, 2533460.021475995, 3302262.1820069975, 2934000, 2924000, 3326000,
         3132714.785188478, 4482000]
loss2 = [6868000, 10567014.81795604, 7146000, 7572000, 7680000, 7176455.035555141, 8254000, 5641999.312590837,
         6147638.373011272, 13873513.48782336, 6942000, 9413235.489025157, 8402000, 5336000, 9676000, 7796000,
         11659198.093317661, 9220514.309734384, 8244962.554841987, 8592636.830676384]

# Generate independent x-axis positions for each list
x1 = [1] * len(loss1)  # Plot `loss1` at x=1
x2 = [2] * len(loss2)  # Plot `loss2` at x=2

# Plot the data
plt.figure(figsize=(8, 6))
plt.scatter(x1, loss1, label="optimised policy", color='blue', alpha=0.7, edgecolor='k')
plt.scatter(x2, loss2, label="random policy", color='orange', alpha=0.7, edgecolor='k')

# Add labels and title
plt.xticks([1, 2], ["optimised policy", "random policy"])
plt.ylabel("Weighted Waiting Time", fontsize=12)
plt.title("Performance Comparison", fontsize=14)
plt.legend(loc="upper right")
plt.grid(axis='y', linestyle='--', alpha=0.6)

plt.xlim(0.3, 2.7)

plt.savefig("loss_comparison_plot.png", dpi=300, bbox_inches='tight')
# Show the plot
plt.tight_layout()
plt.show()
