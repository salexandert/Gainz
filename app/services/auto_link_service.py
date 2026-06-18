class AutoLinkService:
    MIN_UNLINKED_QUANTITY = 0.000001

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

    def selected_year(self, year_value):
        if year_value is None:
            return None

        normalized = str(year_value).strip()
        if normalized in ("", "All Time"):
            return None

        return int(normalized)

    def assets_with_unlinked_sales(self, transactions, year=None, min_unlinked=None):
        min_unlinked = min_unlinked or self.MIN_UNLINKED_QUANTITY
        assets = set()

        for trans in transactions:
            if trans.trans_type != "sell":
                continue

            if trans.unlinked_quantity <= min_unlinked:
                continue

            if year is not None and trans.time_stamp.year != year:
                continue

            assets.add(trans.symbol)

        return sorted(assets)

    def auto_link_unlinked_sales(
        self,
        transactions,
        algo="fifo",
        year=None,
        save_description=None,
    ):
        if algo not in self.DESCRIPTIONS:
            raise ValueError(f"Unsupported auto-link algorithm: {algo}")

        assets_needing_links = self.assets_with_unlinked_sales(transactions, year=year)
        before_link_count = len(transactions.links)
        failures = []

        for asset in assets_needing_links:
            failures.extend(transactions.auto_link(asset=asset, algo=algo, year=year))

        links_created = len(transactions.links) - before_link_count

        if links_created > 0:
            transactions.save(
                description=save_description or f"{self.DESCRIPTIONS[algo]} across all assets"
            )

        if links_created > 0:
            method_label = algo.replace("_", " ").upper()
            message = (
                f"Added {links_created} {method_label} basis link(s) across "
                f"{len(assets_needing_links)} asset(s) for review."
            )
        elif assets_needing_links:
            message = (
                "No new FIFO links could be created. Review basis lots, missing acquisitions, "
                "or unsupported activity for the listed assets."
            )
        else:
            message = "No assets currently have unlinked sales available for FIFO Auto Link."

        return {
            "message": message,
            "links_created": links_created,
            "fixed_assets": assets_needing_links,
            "failures": failures,
            "algo": algo,
            "year": year,
        }
