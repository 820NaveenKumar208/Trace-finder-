// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * FraudLog – VerifyFlow Smart Contract
 * Stores tamper-proof audit records of fraud analysis results.
 */
contract FraudLog {

    struct Transaction {
        string  imageHash;
        uint256 riskScore;
        uint256 timestamp;
        address submitter;
    }

    Transaction[] public transactions;

    event TransactionStored(
        string  indexed imageHash,
        uint256 riskScore,
        uint256 timestamp,
        address submitter
    );

    /**
     * Store a new fraud analysis record on-chain.
     * @param imageHash   SHA-256 hex string of the uploaded image
     * @param riskScore   Risk score 0–100
     * @param timestamp   Unix timestamp of the analysis
     */
    function storeTransaction(
        string  memory imageHash,
        uint256        riskScore,
        uint256        timestamp
    ) public {
        Transaction memory t = Transaction({
            imageHash:  imageHash,
            riskScore:  riskScore,
            timestamp:  timestamp,
            submitter:  msg.sender
        });
        transactions.push(t);
        emit TransactionStored(imageHash, riskScore, timestamp, msg.sender);
    }

    /// Return the total number of stored records
    function getCount() public view returns (uint256) {
        return transactions.length;
    }

    /// Retrieve a record by index
    function getTransaction(uint256 index)
        public view
        returns (string memory, uint256, uint256, address)
    {
        require(index < transactions.length, "Index out of bounds");
        Transaction memory t = transactions[index];
        return (t.imageHash, t.riskScore, t.timestamp, t.submitter);
    }
}
