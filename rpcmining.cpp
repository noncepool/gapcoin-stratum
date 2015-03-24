
Value submitblock(const Array& params, bool fHelp)
{
    if (fHelp || params.size() < 1 || params.size() > 2)
        throw runtime_error(
            "submitblock \"hexdata\" ( \"jsonparametersobject\" )\n"
            "\nAttempts to submit new block to network.\n"
            "The 'jsonparametersobject' parameter is currently ignored.\n"
            "See https://en.gapcoin.it/wiki/BIP_0022 for full specification.\n"

            "\nArguments\n"
            "1. \"hexdata\"    (string, required) the hex-encoded block data to submit\n"
            "2. \"jsonparametersobject\"     (string, optional) object of optional parameters\n"
            "    {\n"
            "      \"workid\" : \"id\"    (string, optional) if the server provided a workid, it MUST be included with submissions\n"
            "    }\n"
            "\nResult:\n"
            "\nExamples:\n"
            + HelpExampleCli("submitblock", "\"mydata\"")
            + HelpExampleRpc("submitblock", "\"mydata\"")
        );

    vector<unsigned char> vchData = ParseHex(params[0].get_str());
    if (vchData.size() <= 86)
        throw JSONRPCError(RPC_INVALID_PARAMETER, "Invalid parameter");

    CBlock* pdata = (CBlock*)&vchData[0];
    CBlock pblock;

    pblock.nAdd.clear();
    for (unsigned int i = 86; i < vchData.size(); i++) {
      pblock.nAdd.push_back(vchData[i]);
    }

    pblock.nVersion  = pdata->nVersion;
    pblock.hashPrevBlock = pdata->hashPrevBlock;
    pblock.hashMerkleRoot = pdata->hashMerkleRoot;
    pblock.nTime  = pdata->nTime;
    pblock.nDifficulty = pdata->nDifficulty;
    pblock.nNonce = pdata->nNonce;
    pblock.nShift = pdata->nShift;

    if (params.size() > 1) {
        vector<unsigned char> txData(ParseHex(params[1].get_str()));
        CDataStream ssTx(txData, SER_NETWORK, PROTOCOL_VERSION);
        std::vector<CTransaction> ptxs;
        try {
            ssTx >> ptxs;
        }
        catch (std::exception &e) {
            throw JSONRPCError(RPC_DESERIALIZATION_ERROR, "Transaction decode failed");
        }
        pblock.vtx = ptxs;
    }

    CValidationState state;
    bool fAccepted = ProcessBlock(state, NULL, &pblock);
    if (!fAccepted)
        return "rejected"; // TODO: report validation state

    return Value::null;
}

