// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IUSDC
 * Arc Testnet USDC ERC-20: 0x3600000000000000000000000000000000000000
 * IMPORTANT: ERC-20 interface = 6 decimals. Native gas token = 18 decimals.
 * Always use the ERC-20 interface (6 decimals) for transfers and math.
 */
interface IUSDC {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function decimals() external view returns (uint8);
}

