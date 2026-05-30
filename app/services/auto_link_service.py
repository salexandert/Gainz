class AutoLinkService:
    DESCRIPTIONS = {
        "fifo": "Auto Linked with FIFO",
        "filo": "Auto Linked with FILO",
        "min_gain_long": "Auto Linked with Min Gain Long",
        "min_gain": "Auto Linked with Min Gain",
    }

    def auto_link(self, transactions, asset=None, algo="fifo", year=None):
        if algo not in self.DESCRIPTIONS:
            raise ValueError(f"Unsupported auto-link algorithm: {algo}")

        transactions.auto_link(asset=asset, algo=algo, year=year)
        transactions.save(description=self.DESCRIPTIONS[algo])

        return f"Auto Link using {algo} Successful!"
