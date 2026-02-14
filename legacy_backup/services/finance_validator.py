import logging

logger = logging.getLogger('finance_validator')

class FinanceValidator:
    """
    Enforces Strict Mode Financial Rules.
    """
    
    @staticmethod
    def validate_transfer(source: dict, dest: dict) -> tuple[bool, str]:
        """
        Validates if a transfer is allowed between two wallets based on Category and Network.
        Returns: (is_valid, error_message)
        """
        src_cat = source.get('category', 'Personal')
        src_net = source.get('network', 'Unknown')
        
        dst_cat = dest.get('category', 'Personal')
        dst_net = dest.get('network', 'Unknown')
        
        # Rule 1: TradFi (Bank)
        if src_cat == 'TradFi':
            # Can send to: TradFi (Bank Transfer), CeFi (Deposit to Exchange), Personal (Cash Withdrawal)
            if dst_cat in ['TradFi', 'CeFi', 'Personal']:
                return True, ""
            return False, f"❌ Cannot transfer from **TradFi** ({src_net}) directly to **{dst_cat}** ({dst_net}). Use an Exchange."

        # Rule 2: CeFi (Exchange)
        if src_cat == 'CeFi':
            # Exchange is the bridge. Can send anywhere basically.
            return True, ""

        # Rule 3: DeFi (Crypto Wallet)
        if src_cat == 'DeFi':
            # Can send to: CeFi (Deposit to Exchange)
            if dst_cat == 'CeFi':
                return True, ""
            
            # Can send to: DeFi (BUT MUST BE SAME NETWORK)
            if dst_cat == 'DeFi':
                if src_net == dst_net:
                    return True, ""
                return False, f"❌ Network Mismatch! Cannot send **{src_net}** to **{dst_net}**. Bridge or Exchange required."
            
            return False, f"❌ Cannot transfer from **DeFi** directly to **{dst_cat}**. Deposit to Exchange first."

        # Rule 4: Personal (Cash)
        if src_cat == 'Personal':
            # Can deposit to Bank or give to other Person
            if dst_cat in ['TradFi', 'Personal']:
                return True, ""
            return False, f"❌ Cannot deposit Cash directly to **{dst_cat}**. Deposit to Bank first."

        return True, ""
