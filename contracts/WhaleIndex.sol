// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/IUSDC.sol";
import "./interfaces/ICircleGateway.sol";

/**
 * @title WhaleIndex
 * @notice Arc-native ERC-20 index token (ARCM) backed 1:1 by USDC.
 *
 * Users deposit USDC → receive ARCM tokens.
 * Users burn ARCM tokens → receive USDC back.
 *
 * A keeper (off-chain Python aggregator) calls rebalance() weekly,
 * passing a new allocation vector derived from:
 *   1. Hyperliquid whale migration signal (80% weight)
 *   2. TradingAgents-CN translation alpha signal (20% weight)
 *
 * Circle Gateway is called inside rebalance() to move USDC cross-chain
 * to match the target allocation across Hyperliquid forks.
 *
 * ─────────────────────────────────────────────────────────────────────
 * Arc Testnet deployment addresses (as of May 2026):
 *   USDC ERC-20:   0x3600000000000000000000000000000000000000
 *   Chain ID:      5042002
 *   RPC:           https://rpc.testnet.arc.network
 *   Explorer:      https://testnet.arcscan.app
 *   Faucet:        https://faucet.circle.com
 * ─────────────────────────────────────────────────────────────────────
 */
contract WhaleIndex {

    // ─── State ───────────────────────────────────────────────────────

    string  public constant name     = "ArcMigrant Whale Index";
    string  public constant symbol   = "ARCM";
    uint8   public constant decimals = 6; // mirrors USDC 6-decimal precision

    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    IUSDC           public immutable usdc;
    ICircleGateway  public immutable gateway;
    address         public keeper;    // off-chain agent authorised to rebalance
    address         public owner;     // admin — can update keeper

    // Current allocation: dex identifier (bytes32) → basis points (0–10000)
    // Total must equal 10000 (100%).
    mapping(bytes32 => uint16) public allocation;
    bytes32[] public dexKeys; // ordered list of active dex identifiers

    // Cross-chain routing: dex identifier → CCTP destination domain
    mapping(bytes32 => uint32) public dexDomain;

    // Cross-chain routing: dex identifier → recipient vault address on destination
    mapping(bytes32 => address) public dexVault;

    // ─── Events ──────────────────────────────────────────────────────

    event Deposit(address indexed user, uint256 usdcAmount, uint256 arcmMinted);
    event Withdraw(address indexed user, uint256 arcmBurned, uint256 usdcReturned);
    event Rebalanced(bytes32[] dexKeys, uint16[] newBps, uint256 timestamp);
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event KeeperUpdated(address indexed oldKeeper, address indexed newKeeper);

    // ─── Errors ──────────────────────────────────────────────────────

    error NotKeeper();
    error NotOwner();
    error ZeroAmount();
    error InsufficientBalance();
    error AllocationMismatch();  // bps do not sum to 10000
    error ArrayLengthMismatch();
    error TransferFailed();

    // ─── Constructor ─────────────────────────────────────────────────

    /**
     * @param _usdc     Arc Testnet USDC ERC-20: 0x3600000000000000000000000000000000000000
     * @param _gateway  Circle Gateway contract address on Arc Testnet
     * @param _keeper   Initial keeper address (your off-chain signing wallet)
     */
    constructor(
        address _usdc,
        address _gateway,
        address _keeper
    ) {
        usdc    = IUSDC(_usdc);
        gateway = ICircleGateway(_gateway);
        keeper  = _keeper;
        owner   = msg.sender;
    }

    // ─── Modifiers ───────────────────────────────────────────────────

    modifier onlyKeeper() {
        if (msg.sender != keeper) revert NotKeeper();
        _;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    // ─── User-facing: deposit & withdraw ────────────────────────────

    /**
     * @notice Deposit USDC and receive ARCM tokens 1:1.
     * @param usdcAmount Amount of USDC to deposit (6 decimals).
     */
    function deposit(uint256 usdcAmount) external {
        if (usdcAmount == 0) revert ZeroAmount();

        bool ok = usdc.transferFrom(msg.sender, address(this), usdcAmount);
        if (!ok) revert TransferFailed();

        // Mint ARCM 1:1 with USDC (both 6 decimals)
        _mint(msg.sender, usdcAmount);

        emit Deposit(msg.sender, usdcAmount, usdcAmount);
    }

    /**
     * @notice Burn ARCM tokens and receive USDC back 1:1.
     * @param arcmAmount Amount of ARCM to burn (6 decimals).
     */
    function withdraw(uint256 arcmAmount) external {
        if (arcmAmount == 0) revert ZeroAmount();
        if (balanceOf[msg.sender] < arcmAmount) revert InsufficientBalance();

        _burn(msg.sender, arcmAmount);

        bool ok = usdc.transfer(msg.sender, arcmAmount);
        if (!ok) revert TransferFailed();

        emit Withdraw(msg.sender, arcmAmount, arcmAmount);
    }

    // ─── Keeper: rebalance ───────────────────────────────────────────

    /**
     * @notice Update fork allocation and trigger Gateway cross-chain moves.
     *
     * Called weekly by the off-chain Python keeper with the signal aggregator
     * output encoded as parallel arrays.
     *
     * @param keys      Array of dex identifiers (keccak256 of dex name string).
     * @param bps       Allocation in basis points per dex (must sum to 10000).
     * @param domains   CCTP destination domain per dex (0 = stay on Arc).
     * @param vaults    Recipient vault address on destination chain per dex.
     */
    function rebalance(
        bytes32[] calldata keys,
        uint16[]  calldata bps,
        uint32[]  calldata domains,
        address[] calldata vaults
    ) external onlyKeeper {
        uint256 len = keys.length;
        if (
            bps.length     != len ||
            domains.length != len ||
            vaults.length  != len
        ) revert ArrayLengthMismatch();

        // Validate allocation sums to 100%
        uint256 total;
        for (uint256 i; i < len; ++i) {
            total += bps[i];
        }
        if (total != 10_000) revert AllocationMismatch();

        // Clear old allocation
        for (uint256 i; i < dexKeys.length; ++i) {
            delete allocation[dexKeys[i]];
            delete dexDomain[dexKeys[i]];
            delete dexVault[dexKeys[i]];
        }
        delete dexKeys;

        // Write new allocation
        for (uint256 i; i < len; ++i) {
            dexKeys.push(keys[i]);
            allocation[keys[i]] = bps[i];
            dexDomain[keys[i]]  = domains[i];
            dexVault[keys[i]]   = vaults[i];
        }

        // Trigger Gateway transfers for non-Arc allocations
        uint256 vaultBalance = usdc.balanceOf(address(this));
        for (uint256 i; i < len; ++i) {
            if (domains[i] != 0 && vaults[i] != address(0) && bps[i] > 0) {
                uint256 transferAmount = (vaultBalance * bps[i]) / 10_000;
                if (transferAmount > 0) {
                    usdc.approve(address(gateway), transferAmount);
                    gateway.transferUSDC(domains[i], vaults[i], transferAmount);
                }
            }
        }

        emit Rebalanced(keys, bps, block.timestamp);
    }

    // ─── Admin ───────────────────────────────────────────────────────

    /**
     * @notice Update the keeper address.
     * @param newKeeper Address of the new keeper wallet.
     */
    function setKeeper(address newKeeper) external onlyOwner {
        emit KeeperUpdated(keeper, newKeeper);
        keeper = newKeeper;
    }

    // ─── ERC-20 standard functions ───────────────────────────────────

    function transfer(address to, uint256 amount) external returns (bool) {
        if (balanceOf[msg.sender] < amount) revert InsufficientBalance();
        balanceOf[msg.sender] -= amount;
        balanceOf[to]         += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (balanceOf[from] < amount) revert InsufficientBalance();
        if (allowance[from][msg.sender] < amount) revert InsufficientBalance();
        allowance[from][msg.sender] -= amount;
        balanceOf[from]             -= amount;
        balanceOf[to]               += amount;
        emit Transfer(from, to, amount);
        return true;
    }

    // ─── View helpers ────────────────────────────────────────────────

    /**
     * @notice Returns the full current allocation as parallel arrays.
     */
    function getAllocation()
        external
        view
        returns (bytes32[] memory keys, uint16[] memory bps)
    {
        uint256 len = dexKeys.length;
        keys = new bytes32[](len);
        bps  = new uint16[](len);
        for (uint256 i; i < len; ++i) {
            keys[i] = dexKeys[i];
            bps[i]  = allocation[dexKeys[i]];
        }
    }

    /**
     * @notice Total USDC held in the vault.
     */
    function vaultBalance() external view returns (uint256) {
        return usdc.balanceOf(address(this));
    }

    // ─── Internal ────────────────────────────────────────────────────

    function _mint(address to, uint256 amount) internal {
        totalSupply   += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function _burn(address from, uint256 amount) internal {
        totalSupply      -= amount;
        balanceOf[from]  -= amount;
        emit Transfer(from, address(0), amount);
    }
}
