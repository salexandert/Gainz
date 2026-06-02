class AutoLinkService:
    DESCRIPTIONS = {
        "fifo": "Added FIFO basis links for review",
        "filo": "Added FILO basis links for review",
        "min_gain_long": "Added Min Gain Long basis links for review",
        "min_gain": "Added Min Gain basis links for review",
    }

    def auto_link(self, transactions, asset=None, algo="fifo", year=None):
        if algo not in self.DESCRIPTIONS:
            raise ValueError(f"Unsupported auto-link algorithm: {algo}")

        transactions.auto_link(asset=asset, algo=algo, year=year)
        transactions.save(description=self.DESCRIPTIONS[algo])

        return f"Auto Link using {algo} completed. Review generated links before using reports."
